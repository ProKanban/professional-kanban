"""Deterministic release archive contracts."""

import hashlib
from pathlib import Path
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
