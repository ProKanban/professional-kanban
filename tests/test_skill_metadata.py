"""Static contracts for the portable skill and plugin metadata."""

import json
from pathlib import Path
import unittest

from tests.support import REPO_ROOT, SKILL_ROOT


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    self_contained = text.split("---", 2)
    if len(self_contained) < 3:
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    values = {}
    for line in self_contained[1].strip().splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


class SkillMetadataTests(unittest.TestCase):
    def test_only_one_canonical_skill_exists(self):
        skills = list(REPO_ROOT.rglob("SKILL.md"))
        self.assertEqual(skills, [SKILL_ROOT / "SKILL.md"])

    def test_frontmatter_is_portable_and_discriminating(self):
        metadata = frontmatter(SKILL_ROOT / "SKILL.md")
        self.assertEqual(metadata["name"], "professional-kanban")
        self.assertEqual(metadata["license"], "See LICENSE")
        self.assertEqual(
            set(metadata), {"name", "description", "license", "metadata"}
        )
        self.assertLessEqual(len(metadata["description"]), 1024)
        for boundary in ("personal scheduling", "package tracking", "file transfer"):
            self.assertIn(boundary, metadata["description"].lower())

    def test_skill_does_not_hardcode_host_installation_paths(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("~/.claude", text)
        self.assertNotIn("$HOME/.agents", text)
        self.assertIn("${CLAUDE_SKILL_DIR}", text)
        self.assertIn("Python 3.11 or newer", text)
        self.assertIn("Monte Carlo flags", text)
        self.assertIn("Cycle-time flags", text)

    def test_openai_skill_metadata_exists(self):
        text = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        for key in ("display_name:", "short_description:", "brand_color:", "default_prompt:"):
            self.assertIn(key, text)
        self.assertIn("$professional-kanban", text)


class PluginManifestTests(unittest.TestCase):
    def load_json(self, relative):
        return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))

    def test_openai_manifest_has_required_distribution_metadata(self):
        manifest = self.load_json(".codex-plugin/plugin.json")
        self.assertEqual(manifest["name"], "professional-kanban")
        self.assertEqual(manifest["version"], "1.1.0")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["repository"], "https://github.com/ProKanban/professional-kanban")
        self.assertNotIn("apps", manifest)
        self.assertNotIn("mcpServers", manifest)

    def test_claude_manifest_matches_name_and_version(self):
        manifest = self.load_json(".claude-plugin/plugin.json")
        self.assertEqual(manifest["name"], "professional-kanban")
        self.assertEqual(manifest["version"], "1.1.0")

    def test_repo_marketplaces_reference_the_plugin_root(self):
        openai = self.load_json(".agents/plugins/marketplace.json")
        self.assertEqual(openai["plugins"][0]["source"]["path"], ".")
        claude = self.load_json(".claude-plugin/marketplace.json")
        self.assertEqual(claude["plugins"][0]["source"], ".")


if __name__ == "__main__":
    unittest.main()
