"""Reject Lua names that exist neither in this repository nor in the WoW client that runs the code.

luacheck (a pinned release binary cached outside the checkout) reads every root in `.scripts/lua-globals/settings.json`
once per client against `WowGlobals.lua`, the Retail and Forever names `refresh-lua-globals.py` snapshots from
wow-ui-source. A name or API field missing on both clients fails; one missing on a single client fails unless that
client's `missingOn*` allowance lists it. A global the repository sets needs an owned prefix, and replacing a client
global fails. Allowance entries nothing needs any more only warn: commits from the shared tree carry other agents'
references separately. `FILES` limits the report to those files (the edit-time hook); `--pre-push` checks each pushed
commit from a clean export, for repositories that only lint on push.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINT_DIRECTORY = Path(".scripts") / "lua-globals"
SETTINGS = LINT_DIRECTORY / "settings.json"
SNAPSHOT = LINT_DIRECTORY / "WowGlobals.lua"
CHECKER = Path(".scripts") / "check-lua-globals.py"
LUACHECK_VERSION = "1.2.0"
LUACHECK_URL = "https://github.com/lunarmodules/luacheck/releases/download/v{version}/{asset}"
LUACHECK_ASSETS = {
    "win32": ("luacheck.exe", "0f1c69c4d09f1ebb4d8df14c215e4553e2e639bd4cb7bf3c639b0daa6198317b"),
    "linux": ("luacheck", "d68da17fca0697d9e2fb04201f3884abd259fa558b3a449bccaed47f1390defc"),
}
TOOL_CACHE = Path(os.environ.get("ORBIT_TOOL_CACHE") or Path.home() / ".cache" / "orbit-lint")
CLIENTS = {"live": "Retail", "forever": "Forever"}
ALLOWANCE = {"live": "missingOnRetail", "forever": "missingOnForever"}
CODES = ("111", "112", "113", "121", "142", "143")
BOTH_CLIENTS = "3"
PASSED_FILE = "orbit-lua-globals-passed"
DOWNLOAD_TIMEOUT_SECONDS = 60
ARCHIVE_READ_BYTES = 64 * 1024
REPORT = re.compile(r"^(?P<path>.+?):(?P<line>\d+):(?P<col>\d+): \((?P<code>[WE]\d+)\) (?P<message>.*)$")
QUOTED = re.compile(r"'([^']*)'")
IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
XML_NAME = re.compile(r'\bname\s*=\s*"(%s)"' % IDENTIFIER)
CREATE_FRAME_NAME = re.compile(r'CreateFrame\(\s*"[^"]*"\s*,\s*"(%s)"' % IDENTIFIER)
SNAPSHOT_ENTRY = re.compile(r"^    (%s) = (\d)," % IDENTIFIER)
SNAPSHOT_OWNER = re.compile(r"^    (%s) = \{$" % IDENTIFIER)
SNAPSHOT_FIELD = re.compile(r"^        (%s) = (\d)," % IDENTIFIER)


def lua_string(value):
    return '"%s"' % str(value).replace("\\", "\\\\").replace('"', '\\"')


def lua_definitions(names):
    """luacheck globals for `Name` and `Name.field` entries; a field entry extends the snapshot's definition."""
    owners = {}
    for name in names:
        owner, _, field = name.partition(".")
        fields = owners.setdefault(owner, set())
        if field:
            fields.add(field)
    entries = []
    for owner, fields in sorted(owners.items()):
        if fields:
            listed = ", ".join("[%s] = {}" % lua_string(field) for field in sorted(fields))
            entries.append("[%s] = { fields = { %s } }" % (lua_string(owner), listed))
        else:
            entries.append("[%s] = { other_fields = true }" % lua_string(owner))
    return "{ %s }" % ", ".join(entries)


def flatten(groups):
    """Settings group names under a reason; each value is a list of names."""
    return sorted({name for names in groups.values() for name in names})


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def luacheck_binary():
    override = os.environ.get("LUACHECK")
    if override:
        return override
    platform = "win32" if os.name == "nt" else sys.platform
    if platform not in LUACHECK_ASSETS:
        raise SystemExit(f"[FAIL] no pinned luacheck {LUACHECK_VERSION} build for {platform}; set LUACHECK to one")
    asset, digest = LUACHECK_ASSETS[platform]
    binary = TOOL_CACHE / f"luacheck-{LUACHECK_VERSION}" / asset
    if binary.is_file() and sha256(binary) == digest:
        return str(binary)
    binary.parent.mkdir(parents=True, exist_ok=True)
    url = LUACHECK_URL.format(version=LUACHECK_VERSION, asset=asset)
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise SystemExit(f"[FAIL] {url} does not match its pinned SHA-256; refusing to run it")
    staged = binary.with_suffix(".download")
    staged.write_bytes(payload)
    staged.chmod(0o755)
    os.replace(staged, binary)
    return str(binary)


def parallel_flags(binary):
    version = subprocess.run([binary, "--version"], capture_output=True, text=True).stdout
    jobs = os.cpu_count() or 1
    return ["-j", str(jobs)] if "LuaLanes" in version and jobs > 1 else []


def config(root, settings, client):
    return "\n".join(
        [
            "stds.wow = dofile(%s)(%s)" % (lua_string((root / SNAPSHOT).as_posix()), lua_string(client)),
            'std = "lua51+wow"',
            "read_globals = %s" % lua_definitions(flatten(settings["readGlobals"])),
            "globals = %s" % lua_definitions(flatten(settings["writableGlobals"])),
            "exclude_files = { %s }" % ", ".join(lua_string(pattern) for pattern in settings["exclude"]),
            "",
        ]
    )


def run_luacheck(root, settings, client, binary, cache):
    with tempfile.TemporaryDirectory(prefix="orbit-luacheck-") as scratch:
        config_path = Path(scratch) / "luacheckrc.lua"
        config_path.write_text(config(root, settings, client), encoding="utf-8")
        command = [binary, *settings["roots"], "--config", str(config_path), "--formatter", "plain", "--codes"]
        command += ["--no-color", "--only", *CODES, *parallel_flags(binary)]
        command += ["--cache", str(cache)] if cache else ["--no-cache"]
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode > 2:
        raise SystemExit(f"[FAIL] luacheck could not run ({result.returncode}):\n{result.stdout}{result.stderr}")
    findings = []
    for line in result.stdout.splitlines():
        match = REPORT.match(line.strip())
        if match:
            quoted = QUOTED.findall(match["message"])
            path = Path(match["path"]).as_posix()
            findings.append((path, int(match["line"]), int(match["col"]), match["code"], quoted, match["message"]))
    return findings


def owned(name, settings):
    return name.startswith(tuple(settings["ownedPrefixes"]))


def glob_regex(pattern):
    parts = re.split(r"(\*\*/?|\*|\?)", pattern)
    tokens = {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*", "?": "[^/]"}
    return re.compile("^" + "".join(tokens.get(part, re.escape(part)) for part in parts) + "$")


def source_files(root, settings):
    excluded = [glob_regex(pattern) for pattern in settings["exclude"]]
    for top in settings["roots"]:
        for path in sorted((root / top).rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.suffix in (".lua", ".xml") and not any(pattern.match(relative) for pattern in excluded):
                yield path


def declared_frames(texts, settings):
    """Frames named in XML or by a literal `CreateFrame` name become globals without a Lua assignment."""
    names = set()
    for path, text in texts.items():
        names.update(XML_NAME.findall(text) if path.suffix == ".xml" else CREATE_FRAME_NAME.findall(text))
    return {name for name in names if owned(name, settings)}


def snapshot_names(root):
    """Names and `Owner.field` entries the snapshot defines on every client."""
    names, owner = set(), None
    for line in (root / SNAPSHOT).read_text(encoding="utf-8").splitlines():
        entry, field, opened = SNAPSHOT_ENTRY.match(line), SNAPSHOT_FIELD.match(line), SNAPSHOT_OWNER.match(line)
        if opened:
            owner = opened[1]
        elif field and owner:
            if field[2] == BOTH_CLIENTS:
                names.add(f"{owner}.{field[1]}")
        elif entry and entry[2] == BOTH_CLIENTS:
            names.add(entry[1])
    return names


def classify(finding, settings, defined):
    """Return (name, message) for one luacheck warning, or None when the repository owns the name."""
    code, quoted, message = finding[3], finding[4], finding[5]
    name = quoted[-1] if quoted else ""
    if code.startswith("E"):
        return name, message
    if code == "W111":
        if owned(name, settings):
            return None
        return name, f"sets global `{name}`; declare it `local` or give it an owned prefix"
    if code in ("W112", "W113"):
        if name in defined:
            return None
        verb = "mutates" if code == "W112" else "reads"
        return name, f"{verb} `{name}`, which neither this repository nor the client defines"
    if code == "W121":
        return name, f"replaces client global `{name}`; hook it (hooksecurefunc) instead of assigning it"
    field = quoted[0] if len(quoted) > 1 else ""
    return f"{name}.{field}", f"`{name}.{field}` does not exist in the client's API"


def stale_allowances(root, settings, texts, used):
    listed = {key: flatten(settings[key]) for key in ("readGlobals", "writableGlobals")}
    names = sorted({name for group in listed.values() for name in group}, key=len, reverse=True)
    pattern = re.compile(r"(?<![\w.])(%s)(?!\w)" % "|".join(map(re.escape, names))) if names else None
    referenced = set()
    for path, text in texts.items():
        if pattern and path.suffix == ".lua":
            referenced.update(pattern.findall(text))
    always = snapshot_names(root)
    stale = []
    for key, group in listed.items():
        for name in group:
            if name in always:
                stale.append(f"`{name}` is listed under `{key}` but the snapshot now defines it on both clients")
            elif name not in referenced:
                stale.append(f"`{name}` is listed under `{key}` but no linted file references it")
    for client, label in CLIENTS.items():
        for name in sorted(set(settings[ALLOWANCE[client]]) - used[client]):
            stale.append(f"`{name}` is listed under `{ALLOWANCE[client]}` but no {label} finding needs it")
    return stale


def check_tree(root, files=None, use_cache=True):
    settings = json.loads((root / SETTINGS).read_text(encoding="utf-8"))
    binary = luacheck_binary()
    cache_key = hashlib.sha1(str(root).lower().encode("utf-8")).hexdigest()[:16]
    cache = TOOL_CACHE / f"luacheck-{LUACHECK_VERSION}-{cache_key}.cache" if use_cache else None
    runs = {client: run_luacheck(root, settings, client, binary, cache) for client in CLIENTS}
    texts = {path: path.read_text(encoding="utf-8", errors="replace") for path in source_files(root, settings)}
    defined = declared_frames(texts, settings)
    for findings in runs.values():
        defined.update(f[4][-1] for f in findings if f[3] == "W111" and owned(f[4][-1], settings))
    violations = {}
    for client, findings in runs.items():
        for finding in findings:
            verdict = classify(finding, settings, defined)
            if verdict:
                violations.setdefault(finding[:3], {})[client] = verdict
    allowed = {client: set(settings[ALLOWANCE[client]]) for client in CLIENTS}
    used = {client: set() for client in CLIENTS}
    report = []
    for (path, line, col), verdicts in sorted(violations.items()):
        if len(verdicts) == len(CLIENTS):
            report.append((path, line, col, next(iter(verdicts.values()))[1]))
            continue
        ((client, (name, message)),) = verdicts.items()
        if name in allowed[client]:
            used[client].add(name)
            continue
        other = next(label for key, label in CLIENTS.items() if key != client)
        note = f"{message} on {CLIENTS[client]} ({other} only); guard it and list it under `{ALLOWANCE[client]}`"
        report.append((path, line, col, note))
    if files is not None:
        wanted = {Path(os.path.relpath(Path(file).resolve(), root)).as_posix() for file in files}
        return [entry for entry in report if entry[0] in wanted], []
    return report, stale_allowances(root, settings, texts, used)


def print_report(report, stale, label):
    for message in stale:
        print(f"[WARN] {SETTINGS.as_posix()}: {message}; remove it")
    for path, line, col, message in report:
        print(f"[FAIL] {path}:{line}:{col}: {message}")
    if report:
        print(f"[FAIL] {len(report)} Lua global problem(s) in {label}.")
        return 1
    print(f"[PASS] Every Lua global in {label} resolves on Retail and Forever.")
    return 0


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def export(root, commit, destination):
    settings = json.loads(git(root, "show", f"{commit}:{SETTINGS.as_posix()}"))
    paths = [*settings["roots"], CHECKER.as_posix(), LINT_DIRECTORY.as_posix()]
    command = ["git", "-C", str(root), "archive", "--format=tar", commit, "--", *paths]
    archive = subprocess.Popen(command, stdout=subprocess.PIPE)
    with archive.stdout:
        with tarfile.open(fileobj=archive.stdout, mode="r|") as tar:
            tar.extractall(destination, filter="data")
        # tarfile stops at the end marker before Git's final padding has drained.
        while archive.stdout.read(ARCHIVE_READ_BYTES):
            pass
    if archive.wait() != 0:
        raise RuntimeError(f"git archive failed for {commit}")


def pre_push(root, lines):
    passed_path = (root / git(root, "rev-parse", "--git-path", PASSED_FILE)).resolve()
    passed = set(passed_path.read_text(encoding="utf-8").split()) if passed_path.is_file() else set()
    commits = []
    for line in lines:
        parts = line.split()
        # A deletion pushes no content; tag objects check the commit they name.
        if len(parts) == 4 and parts[1].strip("0"):
            commit = git(root, "rev-parse", parts[1] + "^{commit}")
            if commit not in passed and commit not in commits:
                commits.append(commit)
    for commit in commits:
        probe = ["git", "-C", str(root), "cat-file", "-e", f"{commit}:{SETTINGS.as_posix()}"]
        if subprocess.run(probe, capture_output=True).returncode != 0:
            print(f"pre-push: {commit[:10]} predates the Lua-globals gate; nothing to check", flush=True)
            continue
        print(f"pre-push: checking Lua globals in {commit[:10]} from a clean export", flush=True)
        scratch = Path(tempfile.mkdtemp(prefix="orbit-lua-globals-"))
        try:
            export(root, commit, scratch)
            env = {**os.environ, "ORBIT_LUACHECK_CACHE": "0"}
            result = subprocess.run([sys.executable, str(scratch / CHECKER)], cwd=scratch, env=env)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        if result.returncode != 0:
            print(f"pre-push: Lua globals failed on {commit[:10]}; push refused", file=sys.stderr)
            return 1
        with passed_path.open("a", encoding="utf-8") as handle:
            handle.write(commit + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", help="report only these files (the whole tree is still read)")
    parser.add_argument("--pre-push", action="store_true", help="check each commit git is about to push")
    args = parser.parse_args()
    if args.pre_push:
        return pre_push(ROOT, sys.stdin.read().splitlines())
    use_cache = os.environ.get("ORBIT_LUACHECK_CACHE") != "0"
    report, stale = check_tree(ROOT, args.files or None, use_cache=use_cache)
    return print_report(report, stale, ", ".join(args.files) if args.files else ROOT.name)


if __name__ == "__main__":
    sys.exit(main())
