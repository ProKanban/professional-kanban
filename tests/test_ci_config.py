"""Static supply-chain contracts for GitHub workflows."""

import re
import unittest

from tests.support import REPO_ROOT


class WorkflowTests(unittest.TestCase):
    def workflow(self, name: str) -> str:
        path = REPO_ROOT / ".github" / "workflows" / name
        self.assertTrue(path.is_file(), name)
        return path.read_text(encoding="utf-8")

    def test_ci_covers_supported_python_and_release_checks(self):
        workflow = self.workflow("ci.yml")
        for version in ('"3.11"', '"3.12"', '"3.13"', '"3.14"'):
            self.assertIn(version, workflow)
        for command in (
            "python -m unittest discover -v",
            "scripts/build_release.py",
            "gh skill publish --dry-run",
            "claude plugin validate",
            "git diff --exit-code",
        ):
            self.assertIn(command, workflow)
        self.assertNotIn("pull_request_target", workflow)

    def test_all_actions_are_pinned_to_full_commit_shas(self):
        for name in ("ci.yml", "release.yml"):
            workflow = self.workflow(name)
            refs = re.findall(r"^\s*uses:\s*[^#\s]+@([^\s#]+)", workflow, re.MULTILINE)
            self.assertTrue(refs, name)
            for ref in refs:
                self.assertRegex(ref, r"^[0-9a-f]{40}$", f"{name}: {ref}")

    def test_release_is_tag_only_attested_and_version_checked(self):
        workflow = self.workflow("release.yml")
        self.assertIn("tags:", workflow)
        self.assertIn("'v*'", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("attestations: write", workflow)
        self.assertIn("attest-build-provenance", workflow)
        self.assertIn("Verify release version", workflow)
        self.assertIn("gh release", workflow)


if __name__ == "__main__":
    unittest.main()
