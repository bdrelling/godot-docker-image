import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import godot_versions as versions


def release(tag, **extra):
    return {
        "tag_name": tag,
        "draft": False,
        "prerelease": False,
        "assets": [{"name": f"Godot_v{tag}_{suffix}"} for suffix in (
            "linux.x86_64.zip", "linux.arm64.zip", "export_templates.tpz"
        )],
        **extra,
    }


class GodotVersionsTests(unittest.TestCase):
    def setUp(self):
        builds = Path(__file__).resolve().parents[1] / ".builds"
        builds.mkdir(exist_ok=True)
        directory = tempfile.TemporaryDirectory(dir=builds)
        self.addCleanup(directory.cleanup)
        self.catalog = Path(directory.name) / "versions.json"
        self.body = Path(directory.name) / "body.md"
        self.catalog.write_text('["4.7-stable"]\n')

    def test_selects_all_stable_releases_in_numeric_order(self):
        releases = [release(tag) for tag in (
            "4.10-stable", "4.8-beta1", "4.9-stable", "3.6-stable",
            "4.7.2-stable", "5.0-stable", "4.6.3-stable", "4.7.1-stable",
        )]
        releases += [release("4.8-stable", prerelease=True), release("4.11-stable", draft=True)]
        actual = versions.missing_releases(["4.7-stable"], releases)
        self.assertEqual([r["tag_name"] for r in actual], [
            "4.7.1-stable", "4.7.2-stable", "4.9-stable", "4.10-stable",
        ])

    def test_late_older_minor_patch_is_included(self):
        actual = versions.missing_releases(["4.7-stable", "4.8-stable"], [release("4.7.3-stable")])
        self.assertEqual(actual[0]["tag_name"], "4.7.3-stable")

    def test_missing_assets_fail_without_changing_catalog(self):
        original = self.catalog.read_bytes()
        for suffix in ("linux.x86_64.zip", "linux.arm64.zip", "export_templates.tpz"):
            broken = release("4.7.2-stable")
            broken["assets"] = [a for a in broken["assets"] if not a["name"].endswith(suffix)]
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, "missing required assets"):
                versions.update_catalog(self.catalog, [release("4.7.1-stable"), broken], self.body)
            self.assertEqual(self.catalog.read_bytes(), original)
            self.assertFalse(self.body.exists())

    def test_update_links_every_release_and_is_idempotent(self):
        releases = [release("4.7.2-stable"), release("4.7.1-stable")]
        with contextlib.redirect_stdout(io.StringIO()):
            versions.update_catalog(self.catalog, releases, self.body)
        expected = ["4.7-stable", "4.7.1-stable", "4.7.2-stable"]
        self.assertEqual(versions.read_catalog(self.catalog), expected)
        body = self.body.read_text()
        for tag in expected[1:]:
            self.assertIn(f"https://github.com/godotengine/godot-builds/releases/tag/{tag}", body)
            self.assertIn(f"https://godotengine.org/download/archive/{tag}/", body)
            self.assertIn(f"godot-interactive-changelog/#{tag.removesuffix('-stable')}", body)
        before = self.catalog.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            versions.update_catalog(self.catalog, releases, self.body)
        self.assertEqual(self.catalog.read_bytes(), before)
        self.assertTrue(self.body.exists())

    def test_invalid_catalogs_are_rejected(self):
        for catalog in ([], ["4.8-stable", "4.7-stable"], ["4.7-stable", "4.7.0-stable"], ["5.0-stable"]):
            self.catalog.write_text(json.dumps(catalog))
            with self.subTest(catalog=catalog), self.assertRaises(ValueError):
                versions.read_catalog(self.catalog)

    def test_paginates_past_prerelease_only_first_page(self):
        first_page = [release("4.8-beta1", prerelease=True)] * 100
        pages = [io.BytesIO(json.dumps(page).encode()) for page in (
            first_page, [release("4.7.2-stable")]
        )]
        with patch.object(versions.urllib.request, "urlopen", side_effect=pages) as fetch:
            actual = versions.fetch_releases()
        self.assertEqual(len(actual), 101)
        self.assertIn("page=2", fetch.call_args.args[0].full_url)
        self.assertEqual(versions.missing_releases(["4.7-stable"], actual)[0]["tag_name"], "4.7.2-stable")

    def test_network_error_propagates(self):
        with patch.object(versions.urllib.request, "urlopen", side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                versions.fetch_releases()

    def test_cli_uses_catalog_and_rejects_untracked_manual_version(self):
        script = str(Path(versions.__file__))
        command = [sys.executable, script, "matrix", "--catalog", str(self.catalog)]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), ["4.7-stable"])
        result = subprocess.run(command + ["--version", "4.8-beta1"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be present", result.stderr)


if __name__ == "__main__":
    unittest.main()
