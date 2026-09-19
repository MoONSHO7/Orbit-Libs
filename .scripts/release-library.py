"""Build one committed library through BigWigs, then publish its verified runtime."""

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import uuid
from urllib.parse import quote
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FIRST_VERSIONS = {"LibOrbitUI": "1.1", "LibOrbitColorPicker": "1.2", "LibOrbitGlow": "1.8", "LibOrbitSearch": "1.0"}
LIBSTUB_COMMIT = "d0d26a9a58eade74964ea95114ca0ab593271b1b"
LIBSTUB_URL = "https://github.com/wowace-clone/LibStub"


def run(*args, cwd=None, env=None, binary=False):
    result = subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=True, text=not binary)
    return result.stdout if binary else result.stdout.strip()


def git(*args, cwd=ROOT, binary=False, env=None):
    return run("git", *args, cwd=cwd, binary=binary, env=env)


def output(**values):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            for key, value in values.items():
                stream.write(f"{key}={value}\n")


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def safe_path(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
        raise ValueError(f"Unsafe archive path: {value}")
    return path


def archive_files(data):
    files = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
        for entry in archive.infolist():
            safe_path(entry.filename)
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode) or (not entry.is_dir() and mode and not stat.S_ISREG(mode)):
                raise ValueError(f"Archive contains a nonordinary file: {entry.filename}")
            if entry.is_dir():
                continue
            if entry.filename in files:
                raise ValueError(f"Archive repeats a file: {entry.filename}")
            files[entry.filename] = archive.read(entry)
    return files


def select_version(library, commit):
    pattern = re.compile(re.escape(library) + r"-((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))")
    versions = {}
    for tag in git("tag", "--list", library + "-*").splitlines():
        match = pattern.fullmatch(tag)
        if match:
            versions[tuple(map(int, match[1].split(".")))] = tag
    if versions:
        latest = versions[max(versions)]
        git("merge-base", "--is-ancestor", latest, commit)
        for version in sorted(versions, reverse=True):
            if git("rev-parse", versions[version] + "^{commit}") == commit:
                return ".".join(map(str, version))
        major, minor = max(versions)
        return f"{major}.{minor + 1}"
    return FIRST_VERSIONS[library]


def prepare(library, work, revision):
    commit = git("rev-parse", revision + "^{commit}")
    version = select_version(library, commit)
    runtime = library + "-1.0"
    files = archive_files(git("-c", "core.autocrlf=false", "-c", "core.eol=lf", "archive", "--format=zip", commit + ":" + library, binary=True))
    if any(PurePosixPath(path).name == ".env" or PurePosixPath(path).name.startswith(".env.") for path in files):
        raise ValueError("Library snapshot must not contain environment files")
    if files.get("LICENSE") != files.get(runtime + "/LICENSE") or "LICENSE" not in files:
        raise ValueError("Root and embedded library licenses must match")
    work.mkdir()
    stage = work / "stage"
    stage.mkdir()
    timestamp = git("show", "-s", "--format=%ct", commit)
    for name, content in files.items():
        path = stage.joinpath(*PurePosixPath(name).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        os.utime(path, (int(timestamp), int(timestamp)))
    if library != "LibOrbitGlow":
        (stage / (runtime + ".toc")).write_text("## Interface: 120100\n", encoding="utf-8")
    (stage / ".release-notes.md").write_text(f"{library} {version}\n\nSource commit: {commit}\n", encoding="utf-8")
    git("init", "--quiet", cwd=stage)
    git("config", "core.autocrlf", "false", cwd=stage)
    git("add", "--force", "--all", cwd=stage)
    env = dict(os.environ, GIT_AUTHOR_DATE=timestamp + " +0000", GIT_COMMITTER_DATE=timestamp + " +0000")
    git("-c", "user.name=Orbit library packaging", "-c", "user.email=packaging@localhost", "commit", "--quiet", "-m", f"Package {library} {version}", cwd=stage, env=env)
    git("tag", version, cwd=stage)
    git("remote", "add", "origin", "https://github.com/" + os.environ.get("GH_REPO", "MoONSHO7/Orbit-Libs") + ".git", cwd=stage)
    plan = {"library": library, "runtime": runtime, "version": version, "tag": library + "-" + version, "commit": commit}
    save(work / "plan.json", plan)
    output(stage=stage, version=version, tag=plan["tag"], curse_project=1586462 if library == "LibOrbitGlow" else 0)
    print(json.dumps(plan))


def expected_payload(plan, work):
    runtime = plan["runtime"]
    files = archive_files(git("-c", "core.autocrlf=false", "-c", "core.eol=lf", "archive", "--format=zip", plan["commit"] + ":" + plan["library"], binary=True))
    expected = {name: content for name, content in files.items() if name.startswith(runtime + "/") and PurePosixPath(name).name != "README.md"}
    if plan["library"] == "LibOrbitGlow":
        import yaml
        metadata = yaml.safe_load(files[".pkgmeta"])
        external = metadata["externals"][runtime + "/LibStub"]
        if external != {"url": LIBSTUB_URL, "commit": LIBSTUB_COMMIT}:
            raise ValueError("Glow must pin the validated LibStub source commit")
        repository = work / "libstub-source"
        if not repository.exists():
            git("init", "--quiet", str(repository))
            git("fetch", "--quiet", "--depth=1", LIBSTUB_URL, LIBSTUB_COMMIT, cwd=repository, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        content = git("show", LIBSTUB_COMMIT + ":LibStub.lua", cwd=repository, binary=True)
        expected[runtime + "/LibStub/LibStub.lua"] = content
        toc = runtime + "/" + runtime + ".toc"
        expected[toc] = expected[toc].replace(b"@project-version@", plan["version"].encode())
    for name in expected:
        path = PurePosixPath(name)
        if path.suffix not in {".lua", ".xml", ".tga", ".toc"} and path.name != "LICENSE":
            raise ValueError(f"Unexpected authored runtime file: {name}")
    if expected.get(runtime + "/LICENSE") != files["LICENSE"]:
        raise ValueError("Embedded license differs from the source license")
    return expected


def verify_closure(plan, files):
    from lupa.lua51 import LuaRuntime
    loaded = set()
    runtime = plan["runtime"]
    def visit(name):
        safe_path(name)
        if name in loaded:
            raise ValueError(f"Repeated runtime include: {name}")
        loaded.add(name)
        content = files[name]
        if name.endswith(".xml"):
            for node in ET.fromstring(content).iter():
                if node.tag.rsplit("}", 1)[-1] in {"Script", "Include"}:
                    visit((PurePosixPath(name).parent / node.attrib["file"].replace("\\", "/")).as_posix())
        elif name.endswith(".toc"):
            for line in content.decode("utf-8").splitlines():
                if line.strip() and not line.lstrip().startswith("#"):
                    visit((PurePosixPath(name).parent / line.strip().replace("\\", "/")).as_posix())
    entry = runtime + "/" + runtime + (".toc" if plan["library"] == "LibOrbitGlow" else ".xml")
    visit(entry)
    if {name for name in files if name.endswith((".lua", ".xml"))} != {name for name in loaded if name.endswith((".lua", ".xml"))}:
        raise ValueError("Lua/XML files are absent from the runtime load closure")
    compile_lua = LuaRuntime().eval("function(source, name) local fn, err = loadstring(source, name); assert(fn, err) end")
    for name in loaded:
        if name.endswith(".lua"):
            compile_lua(files[name].decode("utf-8"), name)


def check_archive(plan, work, archive):
    expected = expected_payload(plan, work)
    actual = archive_files(archive.read_bytes())
    if actual != expected:
        missing = sorted(expected.keys() - actual.keys())
        extra = sorted(actual.keys() - expected.keys())
        changed = sorted(name for name in expected.keys() & actual.keys() if expected[name] != actual[name])
        raise ValueError(f"Runtime mismatch: missing={missing}, extra={extra}, changed={changed}")
    verify_closure(plan, actual)
    return hashlib.sha256(archive.read_bytes()).hexdigest()


def verify(plan, work):
    archives = list((work / "release").glob("*.zip"))
    if len(archives) != 1:
        raise ValueError("Expected one packaged runtime ZIP")
    archive = archives[0]
    if archive.name != f"{plan['runtime']}-{plan['version']}.zip":
        raise ValueError("Packager used the wrong library version")
    check_archive(plan, work, archive)
    files = archive_files(archive.read_bytes())
    timestamp = max(315532800, int(git("show", "-s", "--format=%ct", plan["commit"])))
    date_time = datetime.fromtimestamp(timestamp, timezone.utc).timetuple()[:6]
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as normalized:
        for name in sorted(files):
            entry = zipfile.ZipInfo(name, date_time)
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            normalized.writestr(entry, files[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    Path(str(archive) + ".sha256").write_text(f"{checksum}  {archive.name}\n", encoding="utf-8")
    source = dict(plan, archive=archive.name, sha256=checksum, runtimePath=plan["library"] + "/" + plan["runtime"])
    save(work / "release" / "source.json", source)
    if plan["library"] == "LibOrbitGlow":
        save(work / "release" / "release.json", {"releases": [{"name": plan["runtime"], "version": plan["version"], "filename": archive.name, "nolib": False, "metadata": [{"flavor": "mainline", "interface": 120100}]}]})
    save(work / "verified.json", source)
    print(f"Verified {archive.name}: {checksum}")


def api(path, *args, missing=False):
    result = subprocess.run(["gh", "api", "repos/" + os.environ["GH_REPO"] + path, *args], capture_output=True, text=True)
    if result.returncode:
        try:
            error = json.loads(result.stdout)
        except json.JSONDecodeError:
            error = {}
        if missing and str(error.get("status")) == "404":
            return None
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout) if result.stdout.strip() else None


def release(plan, missing=False):
    published = api("/releases/tags/" + quote(plan["tag"], safe=""), missing=True)
    if published:
        return published
    page = 1
    while True:
        releases = api(f"/releases?per_page=100&page={page}")
        matches = [entry for entry in releases if entry["tag_name"] == plan["tag"]]
        if len(matches) > 1:
            raise ValueError("Multiple GitHub releases use this library tag")
        if matches:
            return matches[0]
        if len(releases) < 100:
            if missing:
                return None
            raise ValueError("GitHub release was not found: " + plan["tag"])
        page += 1


def tag_commit(plan):
    reference = api("/git/ref/tags/" + quote(plan["tag"], safe=""), missing=True)
    return api("/commits/" + quote(plan["tag"], safe="")) if reference else None


def ensure_verified(plan, work):
    verified = json.loads((work / "verified.json").read_text(encoding="utf-8"))
    if any(verified[key] != plan[key] for key in plan):
        raise ValueError("Verification belongs to another source/version")
    archive = work / "release" / verified["archive"]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != verified["sha256"]:
        raise ValueError("Validated archive changed before publication")
    return verified


def verify_published(plan, work):
    destination = work / "published"
    destination.mkdir(exist_ok=True)
    run("gh", "release", "download", plan["tag"], "--repo", os.environ["GH_REPO"], "--dir", str(destination), "--pattern", "*.zip", "--pattern", "*.zip.sha256", "--clobber")
    archives = list(destination.glob("*.zip"))
    if len(archives) != 1:
        raise ValueError("Published release must have one runtime ZIP")
    checksum = check_archive(plan, work, archives[0])
    fields = Path(str(archives[0]) + ".sha256").read_text(encoding="utf-8").split()
    if fields != [checksum, archives[0].name]:
        raise ValueError("Published runtime checksum does not match")
    if checksum != ensure_verified(plan, work)["sha256"]:
        raise ValueError("Published ZIP differs from the exact validated archive")


def check_receipts(plan, work, current):
    verified = ensure_verified(plan, work)
    names = {asset["name"] for asset in current["assets"]}
    found = {}
    for name in ("curse-upload-started.json", "curse-upload-complete.json"):
        if name not in names:
            continue
        destination = work / "receipts"
        destination.mkdir(exist_ok=True)
        run("gh", "release", "download", plan["tag"], "--repo", os.environ["GH_REPO"], "--dir", str(destination), "--pattern", name, "--clobber")
        payload = json.loads((destination / name).read_text(encoding="utf-8"))
        if any(payload.get(key) != value for key, value in verified.items()):
            raise ValueError("CurseForge receipt does not match this source/version/archive: " + name)
        if name == "curse-upload-complete.json" and (type(payload.get("curseFileID")) is not int or payload["curseFileID"] <= 0):
            raise ValueError("CurseForge completion receipt requires its confirmed file ID")
        found[name] = payload
    return found


def reserve(plan, work):
    ensure_verified(plan, work)
    current = tag_commit(plan)
    if current and current["sha"] != plan["commit"]:
        raise ValueError("Remote library tag identifies a different source commit")
    if not current:
        api("/git/refs", "--method", "POST", "-f", "ref=refs/tags/" + plan["tag"], "-f", "sha=" + plan["commit"])
    current = release(plan, missing=True)
    if current and not current["draft"]:
        if current["prerelease"]:
            raise ValueError("Existing release is not stable")
        verify_published(plan, work)
        output(published="true")
        print("Preserved verified published release " + current["html_url"])
        return
    if current and current["target_commitish"] != plan["commit"]:
        raise ValueError("Existing draft belongs to another source commit")
    if current and plan["library"] == "LibOrbitGlow":
        receipts = check_receipts(plan, work, current)
        if receipts:
            verify_published(plan, work)
            if "curse-upload-complete.json" not in receipts:
                raise ValueError("Prior CurseForge upload has no completion receipt; reconcile that upload before retrying")
    if not current:
        notes = work / "release-notes.md"
        notes.write_text(f"{plan['library']} {plan['version']}\n\nSource commit: `{plan['commit']}`\n\nConsumer runtime path: `{plan['library']}/{plan['runtime']}`\n", encoding="utf-8")
        run("gh", "release", "create", plan["tag"], "--repo", os.environ["GH_REPO"], "--draft", "--verify-tag", "--target", plan["commit"], "--title", plan["library"] + " " + plan["version"], "--notes-file", str(notes))
    assets = [path for path in (work / "release").iterdir() if path.is_file() and (path.suffix == ".zip" or path.name.endswith(".zip.sha256") or path.name in {"source.json", "release.json"})]
    run("gh", "release", "upload", plan["tag"], "--repo", os.environ["GH_REPO"], *map(str, assets), "--clobber")
    output(published="false")


def curse_request(method, path, body=None, content_type=None):
    headers = {"X-Api-Token": os.environ["CF_API_KEY"], "Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    connection = http.client.HTTPSConnection("wow.curseforge.com", timeout=120)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        content = response.read()
        if response.status != 200:
            raise RuntimeError(f"CurseForge {method} returned HTTP {response.status}; upload attempts are never retried automatically")
        return json.loads(content)
    finally:
        connection.close()


def curse_upload(plan, work):
    if plan["library"] != "LibOrbitGlow":
        raise ValueError("Only Glow uploads to CurseForge")
    verified = ensure_verified(plan, work)
    current = release(plan)
    if not current["draft"]:
        raise ValueError("CurseForge upload requires the reserved draft")
    receipts = check_receipts(plan, work, current)
    if "curse-upload-complete.json" in receipts:
        return
    if "curse-upload-started.json" in receipts:
        raise ValueError("Prior CurseForge upload has no completion receipt; reconcile that upload before retrying")
    verify_published(plan, work)
    versions = curse_request("GET", "/api/game/wow/versions")
    version_ids = [entry["id"] for entry in versions if entry["name"] == "12.1.0" and entry["gameVersionTypeID"] == 517]
    if len(version_ids) != 1:
        raise ValueError("CurseForge must expose exactly one retail 12.1.0 game version")
    metadata = {"displayName": plan["version"], "gameVersions": version_ids, "releaseType": "release", "changelogType": "markdown", "changelog": (work / "stage" / ".release-notes.md").read_text(encoding="utf-8")}
    boundary = "OrbitLibrary" + uuid.uuid4().hex
    archive = work / "release" / verified["archive"]
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="metadata"\r\n\r\n'.encode()
        + json.dumps(metadata).encode()
        + f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{archive.name}"\r\nContent-Type: application/zip\r\n\r\n'.encode()
        + archive.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    )
    started = work / "curse-upload-started.json"
    save(started, verified)
    run("gh", "release", "upload", plan["tag"], "--repo", os.environ["GH_REPO"], str(started))
    result = curse_request("POST", "/api/projects/1586462/upload-file", body, "multipart/form-data; boundary=" + boundary)
    if type(result.get("id")) is not int or result["id"] <= 0:
        raise ValueError("CurseForge did not confirm a new file ID; reconcile the reserved upload")
    completed = work / "curse-upload-complete.json"
    save(completed, dict(verified, curseFileID=result["id"]))
    run("gh", "release", "upload", plan["tag"], "--repo", os.environ["GH_REPO"], str(completed))
    print(f"CurseForge accepted file {result['id']}")


def finish(plan, work):
    ensure_verified(plan, work)
    if tag_commit(plan)["sha"] != plan["commit"]:
        raise ValueError("Release tag moved after validation")
    current = release(plan)
    if plan["library"] == "LibOrbitGlow":
        if "curse-upload-complete.json" not in check_receipts(plan, work, current):
            raise ValueError("Glow needs its CurseForge completion receipt before GitHub publication")
    verify_published(plan, work)
    run("gh", "release", "edit", plan["tag"], "--repo", os.environ["GH_REPO"], "--draft=false")
    published = release(plan)
    if published["draft"] or published["prerelease"]:
        raise ValueError("GitHub release is not published and stable")
    print(published["html_url"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify", "reserve", "curse-upload", "finish"))
    parser.add_argument("library", choices=FIRST_VERSIONS)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--commit", default="HEAD", help="Committed source revision for prepare (default: HEAD)")
    args = parser.parse_args()
    work = args.work.resolve()
    if work.is_relative_to(ROOT) or ROOT.is_relative_to(work):
        parser.error("Packaging work must be outside the source checkout")
    try:
        if args.action == "prepare":
            prepare(args.library, work, args.commit)
        else:
            plan = json.loads((work / "plan.json").read_text(encoding="utf-8"))
            if plan["library"] != args.library:
                raise ValueError("Work directory belongs to another library")
            {"verify": verify, "reserve": reserve, "curse-upload": curse_upload, "finish": finish}[args.action](plan, work)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Library release failed: {error}\n")


if __name__ == "__main__":
    main()
