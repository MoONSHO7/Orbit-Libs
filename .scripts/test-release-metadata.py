"""Exercise Glow's GitHub and CurseForge metadata without publishing."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile


SCRIPT = Path(__file__).with_name("release-library.py")
SPEC = importlib.util.spec_from_file_location("library_release", SCRIPT)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)
RUNTIME = "LibOrbitGlow-1.0"
TOC = f"{RUNTIME}/{RUNTIME}.toc"
PLAN = {"library": "LibOrbitGlow", "runtime": RUNTIME, "version": "9.9", "tag": "LibOrbitGlow-9.9", "commit": "fixture"}
METADATA = [
    {"flavor": "mainline", "interface": 120100},
    {"flavor": "mainline", "interface": 120105},
    {"flavor": "forever", "interface": 16001},
]
VERSIONS = [
    {"id": 1, "name": "12.1.0", "gameVersionTypeID": 517},
    {"id": 2, "name": "12.1.5", "gameVersionTypeID": 517},
    {"id": 3, "name": "1.60.1", "gameVersionTypeID": 88568},
    {"id": 4, "name": "1.60.1", "gameVersionTypeID": 517},
    {"id": 5, "name": "1.0.0", "gameVersionTypeID": 517},
]


class ReleaseMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        (self.work / "release").mkdir()
        (self.work / "stage").mkdir()
        (self.work / "stage" / ".release-notes.md").write_text("Metadata fixture", encoding="utf-8")
        self.archive = self.work / "release" / f"{RUNTIME}-9.9.zip"
        self.files = {TOC: (SCRIPT.parents[1] / "LibOrbitGlow" / TOC).read_bytes()}
        with zipfile.ZipFile(self.archive, "w") as archive:
            entry = zipfile.ZipInfo(TOC)
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, self.files[TOC])

    def test_current_packaged_toc_and_client_specific_ids(self):
        self.assertEqual(release.game_metadata(PLAN, self.files), METADATA)
        self.assertEqual(release.curse_version_ids(METADATA, VERSIONS), [1, 2, 3])

    def test_new_toc_versions_require_no_hardcoded_patch_update(self):
        metadata = release.game_metadata(PLAN, {TOC: b"## Interface: 120105, 16002\n"})
        versions = VERSIONS + [{"id": 6, "name": "1.60.2", "gameVersionTypeID": 88568}]
        self.assertEqual(release.curse_version_ids(metadata, versions), [2, 6])

    def test_invalid_toc_is_rejected(self):
        for toc in (b"", b"## Interface: \n", b"## Interface: 16001,16001\n", b"## Interface: abc\n", b"## Interface: 11507\n", b"## Interface: 16001\n## Interface: 120100\n"):
            with self.subTest(toc=toc), self.assertRaises(ValueError):
                release.game_metadata(PLAN, {TOC: toc})

    def test_missing_or_ambiguous_forever_version_is_rejected(self):
        for versions in (VERSIONS[:2] + VERSIONS[3:], VERSIONS + [VERSIONS[2]]):
            with self.subTest(versions=versions), self.assertRaisesRegex(ValueError, "forever 1.60.1"):
                release.curse_version_ids(METADATA, versions)

    def test_verify_writes_all_github_game_versions(self):
        with patch.object(release, "check_archive"), patch.object(release, "git", return_value="1800000000"), redirect_stdout(io.StringIO()):
            release.verify(PLAN, self.work)
        result = json.loads((self.work / "release" / "release.json").read_text(encoding="utf-8"))
        self.assertEqual(result["releases"][0]["metadata"], METADATA)
        self.assertEqual(result["releases"][0]["filename"], self.archive.name)

    def upload(self, versions):
        verified = dict(PLAN, archive=self.archive.name, sha256="fixture")
        with (
            patch.object(release, "ensure_verified", return_value=verified),
            patch.object(release, "release", return_value={"draft": True}),
            patch.object(release, "check_receipts", return_value={}),
            patch.object(release, "verify_published"),
            patch.object(release, "run"),
            patch.object(release, "curse_request", side_effect=[versions, {"id": 123}]) as request,
            patch.dict("os.environ", {"GH_REPO": "fixture/repository"}),
            redirect_stdout(io.StringIO()),
        ):
            try:
                release.curse_upload(PLAN, self.work)
            finally:
                self.requests = request.call_args_list

    def test_upload_posts_all_game_versions_and_original_zip(self):
        self.upload(VERSIONS)
        args = self.requests[1].args
        self.assertEqual(args[:2], ("POST", "/api/projects/1586462/upload-file"))
        metadata = json.loads(args[2].split(b"\r\n\r\n", 1)[1].split(b"\r\n--", 1)[0])
        self.assertEqual(metadata["gameVersions"], [1, 2, 3])
        self.assertIn(self.archive.read_bytes(), args[2])
        self.assertTrue((self.work / "curse-upload-complete.json").exists())

    def test_missing_forever_version_does_not_reserve_or_upload(self):
        with self.assertRaisesRegex(ValueError, "forever 1.60.1"):
            self.upload(VERSIONS[:2])
        self.assertEqual(len(self.requests), 1)
        self.assertFalse((self.work / "curse-upload-started.json").exists())


if __name__ == "__main__":
    unittest.main()
