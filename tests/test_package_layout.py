"""Contract tests for the repository's canonical skill layout."""

import unittest

from tests.support import REPO_ROOT, SKILL_ROOT


class PackageLayoutTests(unittest.TestCase):
    def test_canonical_skill_has_required_resources(self):
        self.assertTrue((SKILL_ROOT / "SKILL.md").is_file())
        self.assertTrue((SKILL_ROOT / "scripts" / "monte_carlo.py").is_file())
        self.assertTrue((SKILL_ROOT / "scripts" / "cycle_time.py").is_file())
        self.assertTrue((SKILL_ROOT / "references" / "data-prep.md").is_file())
        self.assertFalse((REPO_ROOT / "professional-kanban").exists())


if __name__ == "__main__":
    unittest.main()
