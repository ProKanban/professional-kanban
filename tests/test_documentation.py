"""Release-facing documentation and licensing contracts."""

from pathlib import Path
import tomllib
import unittest

from tests.support import REPO_ROOT, SKILL_ROOT


class DocumentationTests(unittest.TestCase):
    def test_readme_leads_with_branded_value_and_install_path(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        hero = REPO_ROOT / "docs" / "assets" / "readme-hero.svg"

        self.assertTrue(hero.is_file())
        self.assertIn('src="docs/assets/readme-hero.svg"', readme)
        self.assertIn("## Why Professional Kanban?", readme)
        self.assertIn("## See it in action", readme)
        self.assertLess(
            readme.index("## Install in 30 seconds"),
            readme.index("## What it does"),
        )

    def test_readme_has_current_install_paths_and_support_matrix(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for required in (
            "## Install in 30 seconds",
            "ChatGPT",
            "Claude.ai / Claude Desktop",
            "Claude Code",
            "Codex",
            "professional-kanban.skill",
            "/plugin marketplace add ProKanban/professional-kanban",
            "Customize > Skills",
            "Python 3.11",
            "No network",
            "## Troubleshooting",
            "## Update or uninstall",
        ):
            self.assertIn(required, readme)

    def test_documentation_has_no_stale_precanonical_paths_or_runtime(self):
        public_paths = [
            REPO_ROOT / "README.md",
            SKILL_ROOT / "SKILL.md",
            *sorted((SKILL_ROOT / "references").glob("*.md")),
        ]
        markdown = "\n".join(path.read_text(encoding="utf-8") for path in public_paths)
        self.assertNotIn("Python 3.8", markdown)
        self.assertNotIn("cd professional-kanban/scripts", markdown)
        self.assertNotIn("`professional-kanban/references", markdown)
        self.assertNotIn("cp -r professional-kanban-skill/professional-kanban", markdown)

    def test_release_and_community_documents_exist(self):
        for relative in (
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "THIRD_PARTY_NOTICES.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/ISSUE_TEMPLATE/parser.yml",
            ".github/ISSUE_TEMPLATE/forecast.yml",
            ".github/ISSUE_TEMPLATE/documentation.yml",
        ):
            self.assertTrue((REPO_ROOT / relative).is_file(), relative)

    def test_reuse_metadata_maps_all_three_license_classes(self):
        data = tomllib.loads((REPO_ROOT / "REUSE.toml").read_text(encoding="utf-8"))
        identifiers = {
            annotation["SPDX-License-Identifier"]
            for annotation in data["annotations"]
        }
        self.assertEqual(identifiers, {"MIT", "CC-BY-SA-4.0", "CC0-1.0"})
        for identifier in identifiers:
            self.assertTrue((REPO_ROOT / "LICENSES" / f"{identifier}.txt").is_file())

    def test_runtime_scripts_have_spdx_headers(self):
        for path in (SKILL_ROOT / "scripts").glob("*.py"):
            header = path.read_text(encoding="utf-8")[:250]
            self.assertIn("SPDX-FileCopyrightText: 2026 ProKanban.org", header)
            self.assertIn("SPDX-License-Identifier: MIT", header)

    def test_notices_name_source_owners_without_inventing_licenses(self):
        notices = (REPO_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        self.assertIn("Orderly Disruption Limited", notices)
        self.assertIn("Daniel S. Vacanti, Inc.", notices)
        self.assertIn("Prateek Singh", notices)
        self.assertIn("Colleen Johnson", notices)
        self.assertIn("No separate public license notice", notices)
        self.assertEqual(
            notices,
            (SKILL_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8"),
        )

    def test_download_instructions_include_checksum_manifest(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        install_section = readme.split("## Platform support", 1)[0]
        self.assertIn("SHA256SUMS", install_section)
        self.assertLess(readme.index("### Codex"), readme.index("SHA256SUMS"))

    def test_readme_install_commands_are_unpinned(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("professional-kanban@v", readme)
        self.assertNotIn("ProKanban/professional-kanban-skill", readme)

    def test_repository_forces_portable_line_endings(self):
        attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("* text=auto eol=lf", attributes)


if __name__ == "__main__":
    unittest.main()
