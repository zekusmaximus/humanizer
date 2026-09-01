"""Tests for the claude.ai skill packager."""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import package_skills  # noqa: E402


class PackageSkillsTests(unittest.TestCase):
    def test_both_skills_validate_against_the_upload_contract(self):
        for name in package_skills.SKILLS:
            spec = package_skills.SKILLS[name]
            skill_md = ROOT / str(spec["source"]) / "SKILL.md"
            parsed_name, description = package_skills.validate_frontmatter(skill_md, name)
            self.assertEqual(parsed_name, name)
            self.assertTrue(description)
            fields = package_skills.parse_frontmatter(skill_md)
            self.assertTrue(set(fields) <= package_skills.ALLOWED_FRONTMATTER_KEYS, fields.keys())

    def test_humanizer_version_is_recorded_under_metadata(self):
        fields = package_skills.parse_frontmatter(ROOT / "Humanizer" / "SKILL.md")
        self.assertNotIn("version", fields)
        self.assertIn("version", fields.get("metadata", ""))

    def test_archives_have_one_top_level_folder_named_after_the_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            with redirect_stdout(io.StringIO()):
                exit_code = package_skills.main(["--output-dir", directory])
            self.assertEqual(exit_code, 0)
            for name in package_skills.SKILLS:
                archive_path = Path(directory) / f"{name}.zip"
                self.assertTrue(archive_path.is_file(), archive_path)
                with zipfile.ZipFile(archive_path) as archive:
                    names = archive.namelist()
                self.assertTrue(all(entry.startswith(f"{name}/") for entry in names), names[:5])
                self.assertEqual([entry for entry in names if entry.endswith("/SKILL.md")], [f"{name}/SKILL.md"])
                self.assertFalse(any("__pycache__" in entry or entry.endswith(".pyc") for entry in names))
            with zipfile.ZipFile(Path(directory) / "aiproofing-text.zip") as archive:
                names = set(archive.namelist())
            for required in (
                "aiproofing-text/scripts/task_manifest.json",
                "aiproofing-text/scripts/aiproof_runner.py",
                "aiproofing-text/protocols/README.md",
                "aiproofing-text/presets/domain_presets.md",
                "aiproofing-text/benchmark/README.md",
            ):
                self.assertIn(required, names)
            with zipfile.ZipFile(Path(directory) / "humanizer.zip") as archive:
                self.assertEqual(sorted(archive.namelist()), ["humanizer/README.md", "humanizer/SKILL.md"])

    def test_archives_are_deterministic(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            with redirect_stdout(io.StringIO()):
                package_skills.main(["--output-dir", first, "--skill", "humanizer"])
                package_skills.main(["--output-dir", second, "--skill", "humanizer"])
            self.assertEqual(
                (Path(first) / "humanizer.zip").read_bytes(),
                (Path(second) / "humanizer.zip").read_bytes(),
            )

    def test_check_mode_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "package_skills.py"), "--check", "--output-dir", directory],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("humanizer: valid", result.stdout)
            self.assertIn("aiproofing-text: valid", result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_unexpected_frontmatter_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            skill_md = Path(directory) / "SKILL.md"
            skill_md.write_text("---\nname: demo\nversion: 1.0\ndescription: Demo.\n---\n# Demo\n", encoding="utf-8")
            with self.assertRaises(package_skills.PackagingError) as raised:
                package_skills.validate_frontmatter(skill_md, "demo")
            self.assertIn("version", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
