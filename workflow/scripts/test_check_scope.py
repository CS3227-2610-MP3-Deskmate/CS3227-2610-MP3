"""Tests for check_scope.py. Run: python3 -m unittest discover -s workflow/scripts"""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import check_scope
from check_scope import ROOT, in_scope, load_scope, relative_to_root

SCRIPT = ROOT / "workflow" / "scripts" / "check_scope.py"


def run_hook(event):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--hook"],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
    )


def edit_event(role, rel_path):
    event = {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(ROOT / rel_path)},
        "cwd": str(ROOT),
    }
    if role:
        event["agent_type"] = role
    return event


class GlobTest(unittest.TestCase):
    def test_glob_single_star_stays_in_folder(self):
        self.assertTrue(check_scope.matches("src/a.py", ["src/*"]))
        self.assertFalse(check_scope.matches("src/app/a.py", ["src/*"]))

    def test_glob_double_star_spans_folders(self):
        self.assertTrue(check_scope.matches("src/app/views.py", ["src/**"]))
        self.assertTrue(check_scope.matches("src/tests/test_a.py", ["src/**/tests/**"]))
        self.assertTrue(
            check_scope.matches("src/app/tests/test_a.py", ["src/**/tests/**"])
        )
        self.assertFalse(check_scope.matches("src/app/views.py", ["src/**/tests/**"]))

    def test_glob_leading_double_star_matches_root(self):
        self.assertTrue(
            check_scope.matches("requirements.txt", ["**/requirements*.txt"])
        )
        self.assertTrue(
            check_scope.matches("src/requirements-dev.txt", ["**/requirements*.txt"])
        )


class RoleScopeTest(unittest.TestCase):
    def test_implementer_production_code_allowed(self):
        scope = load_scope("implementer")
        for path in [
            "src/tickets/views.py",
            "src/tickets/migrations/0001_initial.py",
            "docs/UserGuide.md",
            "workflow/plans/12-submit-ticket.md",
        ]:
            self.assertTrue(in_scope(path, scope), path)

    def test_implementer_tests_specs_and_dependencies_blocked(self):
        scope = load_scope("implementer")
        for path in [
            "src/tickets/tests/test_views.py",
            "src/tickets/tests/factories.py",
            "src/tickets/tests.py",
            "src/tickets/test_models.py",
            "src/tickets/views_test.py",
            "src/conftest.py",
            "src/e2e/test_submit.py",
            "src/pytest.ini",
            "setup.cfg",
            "src/tox.ini",
            ".coveragerc",
            "workflow/specs/PRODUCT-SPEC.md",
            "src/requirements.txt",
            "pyproject.toml",
            "AGENTS.md",
            ".github/workflows/ci.yml",
            "workflow/agents/implementer.md",
            "workflow/scripts/check_scope.py",
        ]:
            self.assertFalse(in_scope(path, scope), path)

    def test_test_writer_only_tests_allowed(self):
        scope = load_scope("test-writer")
        for path in [
            "src/tickets/tests/test_views.py",
            "src/tickets/tests/factories.py",
            "src/tickets/tests.py",
            "src/tickets/views_test.py",
            "src/e2e/test_submit.py",
            "pytest.ini",
        ]:
            self.assertTrue(in_scope(path, scope), path)
        self.assertFalse(in_scope("src/tickets/views.py", scope))
        self.assertFalse(in_scope("workflow/specs/PRODUCT-SPEC.md", scope))
        self.assertFalse(in_scope("requirements.txt", scope))

    def test_devops_build_and_deploy_files_allowed(self):
        scope = load_scope("devops")
        for path in [
            "Dockerfile",
            ".dockerignore",
            "compose.yaml",
            ".github/workflows/ci.yml",
            "requirements.txt",
            "requirements-dev.txt",
            ".env.example",
            "workflow/plans/1-skeleton.md",
        ]:
            self.assertTrue(in_scope(path, scope), path)

    def test_devops_code_tests_specs_and_secrets_blocked(self):
        scope = load_scope("devops")
        for path in [
            "src/deskmate/settings.py",
            "src/Dockerfile",
            "src/requirements.txt",
            "src/tickets/tests/test_views.py",
            "pytest.ini",
            ".env",
            ".env.production",
            "AGENTS.md",
            "workflow/specs/TECHNICAL-SPEC.md",
            "workflow/agents/devops.md",
            ".github/pull_request_template.md",
        ]:
            self.assertFalse(in_scope(path, scope), path)

    def test_spec_writer_only_specs_allowed(self):
        scope = load_scope("spec-writer")
        self.assertTrue(in_scope("workflow/specs/product/requester.md", scope))
        self.assertFalse(in_scope("src/tickets/views.py", scope))
        self.assertFalse(in_scope("workflow/agents/spec-writer.md", scope))

    def test_reviewers_nothing_allowed(self):
        for role in ["spec-critic", "reviewer", "security-reviewer"]:
            scope = load_scope(role)
            self.assertFalse(in_scope("src/tickets/views.py", scope), role)
            self.assertFalse(in_scope("workflow/specs/PRODUCT-SPEC.md", scope), role)

    def test_load_scope_unknown_role_none(self):
        self.assertIsNone(load_scope("no-such-role"))


class PathTest(unittest.TestCase):
    def test_relative_to_root_inside_repo_forward_slashes(self):
        self.assertEqual(
            relative_to_root(ROOT / "src" / "app" / "views.py"), "src/app/views.py"
        )

    def test_relative_to_root_outside_repo_none(self):
        self.assertIsNone(relative_to_root(ROOT.parent / "elsewhere.txt"))


class HookTest(unittest.TestCase):
    def test_hook_implementer_edits_test_blocked(self):
        result = run_hook(edit_event("implementer", "src/tickets/tests/test_views.py"))
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "implementer may not write src/tickets/tests/test_views.py", result.stderr
        )

    def test_hook_implementer_edits_code_allowed(self):
        self.assertEqual(
            run_hook(edit_event("implementer", "src/tickets/views.py")).returncode, 0
        )

    def test_hook_reviewer_writes_blocked(self):
        self.assertEqual(
            run_hook(edit_event("reviewer", "src/tickets/views.py")).returncode, 2
        )

    def test_hook_write_outside_repo_blocked(self):
        event = edit_event("implementer", "x")
        event["tool_input"]["file_path"] = str(ROOT.parent / "outside.py")
        self.assertEqual(run_hook(event).returncode, 2)

    def test_hook_relative_path_resolved_from_cwd(self):
        event = edit_event("test-writer", "x")
        event["tool_input"]["file_path"] = "src/tickets/tests/test_views.py"
        self.assertEqual(run_hook(event).returncode, 0)
        event["tool_input"]["file_path"] = "src/tickets/views.py"
        self.assertEqual(run_hook(event).returncode, 2)

    def test_hook_codex_patch_any_path_out_of_scope_blocked(self):
        patch = (
            "*** Begin Patch\n*** Update File: src/tickets/views.py\n@@\n-a\n+b\n"
            "*** Add File: src/tickets/tests/test_views.py\n+x\n*** End Patch\n"
        )
        event = {
            "agent_type": "implementer",
            "tool_name": "apply_patch",
            "tool_input": {"command": patch},
            "cwd": str(ROOT),
        }
        result = run_hook(event)
        self.assertEqual(result.returncode, 2)
        self.assertIn("src/tickets/tests/test_views.py", result.stderr)

    def test_hook_codex_patch_in_scope_allowed(self):
        patch = (
            "*** Begin Patch\r\n*** Update File: src/tickets/views.py\r\n"
            "*** Move to: src/tickets/pages.py\r\n*** End Patch\r\n"
        )
        event = {
            "agent_type": "implementer",
            "tool_name": "apply_patch",
            "tool_input": {"command": patch},
            "cwd": str(ROOT),
        }
        self.assertEqual(run_hook(event).returncode, 0)

    def test_hook_codex_patch_extra_spaces_parsed(self):
        patch = (
            "*** Begin Patch\n"
            "***  Update File:  src/tickets/tests/test_views.py \n"
            "*** End Patch\n"
        )
        event = {
            "agent_type": "implementer",
            "tool_name": "apply_patch",
            "tool_input": {"command": patch},
            "cwd": str(ROOT),
        }
        self.assertEqual(run_hook(event).returncode, 2)

    def test_hook_role_edit_without_paths_blocked(self):
        for tool_input in [
            {"command": "*** Begin Patch\n*** End Patch\n"},
            {"patch": "not a patch"},
            {},
        ]:
            event = {
                "agent_type": "implementer",
                "tool_name": "apply_patch",
                "tool_input": tool_input,
                "cwd": str(ROOT),
            }
            self.assertEqual(run_hook(event).returncode, 2, tool_input)

    def test_hook_codex_underscore_name_uses_role_file(self):
        self.assertEqual(
            run_hook(edit_event("test_writer", "src/tickets/views.py")).returncode, 2
        )
        self.assertEqual(
            run_hook(
                edit_event("test_writer", "src/tickets/tests/test_a.py")
            ).returncode,
            0,
        )

    def test_hook_main_session_allowed(self):
        self.assertEqual(
            run_hook(edit_event(None, "src/tickets/tests/test_views.py")).returncode, 0
        )

    def test_hook_agent_without_role_file_allowed(self):
        self.assertEqual(
            run_hook(edit_event("general-purpose", "AGENTS.md")).returncode, 0
        )


class WorkingTreeTest(unittest.TestCase):
    """Runs check_working_tree against a throwaway Git repository."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.git("init", "-q")
        self.write("src/tickets/views.py")
        self.write("src/tickets/tests/test_views.py")
        self.git("add", "src")
        self.git("commit", "-q", "-m", "init")
        self.base = self.git("rev-parse", "HEAD").strip()

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def write(self, rel_path, text="x\n"):
        path = self.root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def check(self, role, base=None):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = check_scope.check_working_tree(role, base, self.root)
        return code, out.getvalue()

    def test_working_tree_in_scope_edits_pass(self):
        self.write("src/tickets/views.py", "y\n")
        self.write("src/tickets/forms.py")
        self.assertEqual(self.check("implementer", self.base)[0], 0)

    def test_working_tree_untracked_out_of_scope_fails(self):
        self.write("src/tickets/tests/test_new.py")
        code, out = self.check("implementer", self.base)
        self.assertEqual(code, 1)
        self.assertIn("src/tickets/tests/test_new.py", out)

    def test_working_tree_deleted_test_fails(self):
        (self.root / "src/tickets/tests/test_views.py").unlink()
        self.assertEqual(self.check("implementer")[0], 1)

    def test_working_tree_staged_rename_checks_old_path(self):
        self.git("mv", "src/tickets/tests/test_views.py", "src/tickets/moved.py")
        code, out = self.check("implementer")
        self.assertEqual(code, 1)
        self.assertIn("src/tickets/tests/test_views.py", out)

    def test_working_tree_agent_commit_caught_with_base(self):
        self.write("src/tickets/tests/test_views.py", "weakened\n")
        self.git("commit", "-q", "-am", "agent commit")
        self.assertEqual(self.check("implementer")[0], 0)  # invisible without a base
        code, out = self.check("implementer", self.base)
        self.assertEqual(code, 1)
        self.assertIn("src/tickets/tests/test_views.py", out)
        self.assertIn("HEAD has moved", out)


if __name__ == "__main__":
    unittest.main()
