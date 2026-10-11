"""Checks that the Claude Code and Codex adapters match the role and skill files.

Run: python3 -m unittest discover -s workflow/scripts
"""

import json
import tomllib
import unittest

from check_scope import ROOT, load_scope

ROLES = sorted(path.stem for path in (ROOT / "workflow" / "agents").glob("*.md"))
SKILLS = sorted(path.stem for path in (ROOT / "workflow" / "skills").glob("*.md"))
CODEX_AGENT_KEYS = {"name", "description", "developer_instructions", "sandbox_mode"}
WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"}


def front_matter(path):
    """Parse simple `key: value` front matter; values must not need YAML quoting."""
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---", f"{path} has no front matter"
    fields = {}
    for line in lines[1:lines.index("---", 1)]:
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def body(path):
    return path.read_text(encoding="utf-8").split("---", 2)[2]


class AdapterTest(unittest.TestCase):
    def test_roles_have_both_adapters(self):
        for role in ROLES:
            claude = front_matter(ROOT / ".claude" / "agents" / f"{role}.md")
            with open(ROOT / ".codex" / "agents" / f"{role}.toml", "rb") as file:
                codex = tomllib.load(file)
            self.assertEqual(claude["name"], role)
            self.assertEqual(codex["name"], role)
            self.assertEqual(claude["description"], codex["description"], role)
            self.assertLessEqual(set(codex), CODEX_AGENT_KEYS, role)
            self.assertIn(f"workflow/agents/{role}.md", body(ROOT / ".claude" / "agents" / f"{role}.md"))
            self.assertIn(f"workflow/agents/{role}.md", codex["developer_instructions"])

    def test_read_only_roles_cannot_write_in_either_tool(self):
        for role in ROLES:
            read_only = not load_scope(role)["writes"]
            tools = {tool.strip() for tool in front_matter(ROOT / ".claude" / "agents" / f"{role}.md")["tools"].split(",")}
            with open(ROOT / ".codex" / "agents" / f"{role}.toml", "rb") as file:
                sandbox = tomllib.load(file)["sandbox_mode"]
            self.assertEqual(read_only, not tools & WRITE_TOOLS, role)
            self.assertEqual(read_only, sandbox == "read-only", role)
            self.assertNotIn("Agent", tools, f"{role} must not spawn agents")

    def test_skills_have_both_adapters(self):
        for skill in SKILLS:
            claude_path = ROOT / ".claude" / "skills" / skill / "SKILL.md"
            codex_path = ROOT / ".codex" / "skills" / skill / "SKILL.md"
            claude, codex = front_matter(claude_path), front_matter(codex_path)
            self.assertEqual(claude["name"], skill)
            self.assertEqual(codex["name"], skill)
            self.assertEqual(claude["description"], codex["description"], skill)
            for path in (claude_path, codex_path):
                self.assertIn(f"workflow/skills/{skill}.md", body(path))

    def test_no_orphan_adapters(self):
        self.assertEqual(sorted(p.stem for p in (ROOT / ".claude" / "agents").glob("*.md")), ROLES)
        self.assertEqual(sorted(p.stem for p in (ROOT / ".codex" / "agents").glob("*.toml")), ROLES)
        for root in (".claude", ".codex"):
            self.assertEqual(sorted(p.parent.name for p in (ROOT / root / "skills").glob("*/SKILL.md")), SKILLS)

    def test_hooks_run_check_scope_on_edits_in_both_tools(self):
        claude = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        codex = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        self.assertLessEqual(set(codex), {"hooks", "description"})  # Codex skips the file otherwise
        for config, tools in [(claude, {"Edit", "Write"}), (codex, {"apply_patch", "Edit", "Write"})]:
            group = config["hooks"]["PreToolUse"][0]
            self.assertLessEqual(tools, set(group["matcher"].split("|")))
            handler = group["hooks"][0]
            for key in [key for key in ("command", "commandWindows") if key in handler]:
                self.assertIn("workflow/scripts/check_scope.py\" --hook", handler[key])
        self.assertTrue(codex["hooks"]["PreToolUse"][0]["hooks"][0]["commandWindows"].endswith("; exit $LASTEXITCODE"))

    def test_slice_is_user_invoked_only_in_both_tools(self):
        self.assertEqual(front_matter(ROOT / ".claude" / "skills" / "slice" / "SKILL.md")["disable-model-invocation"], "true")
        policy = (ROOT / ".codex" / "skills" / "slice" / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", policy)

    def test_descriptions_are_plain_yaml(self):
        paths = [ROOT / ".claude" / "agents" / f"{role}.md" for role in ROLES]
        paths += [ROOT / root / "skills" / skill / "SKILL.md" for root in (".claude", ".codex") for skill in SKILLS]
        for path in paths:
            description = front_matter(path)["description"]
            self.assertNotIn(": ", description, path)
            self.assertNotIn(" #", description, path)


if __name__ == "__main__":
    unittest.main()
