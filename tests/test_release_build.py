"""Deterministic release archive contracts."""

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
import zipfile

from scripts import build_release
from tests.support import SKILL_ROOT


class ReleaseBuildTests(unittest.TestCase):
    def build(self, output: Path):
        return build_release.build_release(output_dir=output)

    def test_two_builds_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = self.build(root / "one")
            second = self.build(root / "two")
            for name in ("professional-kanban.zip", "professional-kanban.skill", "SHA256SUMS"):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

    def test_zip_and_skill_are_the_same_clean_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            output = self.build(Path(temp))
            zip_path = output / "professional-kanban.zip"
            skill_path = output / "professional-kanban.skill"
            self.assertEqual(zip_path.read_bytes(), skill_path.read_bytes())

            expected = {
                "professional-kanban/" + path.relative_to(SKILL_ROOT).as_posix()
                for path in SKILL_ROOT.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix not in {".pyc", ".pyo"}
                and path.name != ".DS_Store"
            }
            with zipfile.ZipFile(zip_path) as archive:
                self.assertEqual(set(archive.namelist()), expected)
                for info in archive.infolist():
                    self.assertTrue(info.filename.startswith("professional-kanban/"))
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                    self.assertEqual((info.external_attr >> 16) & 0o777, 0o644)

    def test_checksums_are_sorted_and_match_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            output = self.build(Path(temp))
            lines = (output / "SHA256SUMS").read_text(encoding="ascii").splitlines()
            self.assertEqual(lines, sorted(lines, key=lambda line: line.split("  ", 1)[1]))
            self.assertEqual(len(lines), 2)
            for line in lines:
                digest, name = line.split("  ", 1)
                actual = hashlib.sha256((output / name).read_bytes()).hexdigest()
                self.assertEqual(digest, actual)

    def test_text_line_endings_do_not_change_release_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            crlf_source = root / "crlf-source"
            shutil.copytree(SKILL_ROOT, crlf_source)
            for path in crlf_source.rglob("*"):
                if path.is_file() and path.suffix in {".md", ".py", ".yaml", ".json", ".csv"}:
                    text = path.read_text(encoding="utf-8")
                    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
            first = root / "lf.zip"
            second = root / "crlf.zip"
            build_release.build_archive(SKILL_ROOT, first)
            build_release.build_archive(crlf_source, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_archive_target_cannot_be_inside_source(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            shutil.copytree(SKILL_ROOT, source)
            with self.assertRaisesRegex(ValueError, "outside the skill source"):
                build_release.build_archive(source, source / "inside.zip")

    def test_archive_carries_redistribution_license_and_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            output = self.build(Path(temp))
            with zipfile.ZipFile(output / "professional-kanban.zip") as archive:
                license_text = archive.read("professional-kanban/LICENSE").decode("utf-8")
                notices = archive.read(
                    "professional-kanban/THIRD_PARTY_NOTICES.md"
                ).decode("utf-8")
            self.assertIn("Permission is hereby granted, free of charge", license_text)
            self.assertIn("No separate public license notice", notices)

    def test_release_version_validates_claude_marketplace(self):
        original = build_release._manifest_version

        def drift_marketplace(path):
            if path.name == "marketplace.json" and path.parent.name == ".claude-plugin":
                return "0.0.0"
            return original(path)

        with mock.patch.object(
            build_release, "_manifest_version", side_effect=drift_marketplace
        ):
            with self.assertRaisesRegex(ValueError, "marketplace.json declares 0.0.0"):
                build_release.validate_release_version("v1.1.0")


if __name__ == "__main__":
    unittest.main()
