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

    def test_release_separates_untrusted_build_from_privileged_publish(self):
        workflow = self.workflow("release.yml")
        self.assertIn("verify-and-build:", workflow)
        self.assertIn("publish:", workflow)
        self.assertIn("needs: verify-and-build", workflow)
        self.assertIn("persist-credentials: false", workflow)
        publish = workflow.split("  publish:", 1)[1]
        self.assertNotIn("actions/checkout", publish)
        self.assertNotIn("python scripts/", publish)
        self.assertIn("contents: write", publish)
        self.assertIn("id-token: write", publish)
        self.assertIn("attestations: write", publish)

    def test_release_enforces_signed_tag_main_ancestry_and_exact_ci(self):
        workflow = self.workflow("release.yml")
        for evidence in (
            'object.type',
            'verification.verified',
            'merge-base --is-ancestor',
            'actions/workflows/ci.yml/runs',
            'head_sha',
            'conclusion == "success"',
        ):
            self.assertIn(evidence, workflow)

    def test_claude_validation_is_exact_and_mandatory(self):
        workflow = self.workflow("ci.yml")
        self.assertIn(
            "actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e",
            workflow,
        )
        self.assertIn('node-version: "24"', workflow)
        self.assertIn("@anthropic-ai/claude-code@2.1.235", workflow)
        self.assertIn(
            "poJ4l/nro9NEZEoLU1txUGMMw92m5P3o6Nh86GfaQuPryvOdKIz/ChlPaq3FDetiaXmoNit3ZkEgnQ1PN7z/dQ==",
            workflow,
        )
        self.assertIn("claude plugin validate --strict .", workflow)
        self.assertNotIn("if command -v claude", workflow)


if __name__ == "__main__":
    unittest.main()
