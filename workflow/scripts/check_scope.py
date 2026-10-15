#!/usr/bin/env python3
"""Check file changes against a role agent's write scope.

A role's scope is the `writes` and `never_writes` lists in the front matter of
workflow/agents/<role>.md. A path is in scope if it matches a `writes` pattern
and no `never_writes` pattern. In patterns, `*` stays within one folder and
`**` spans folders.

Usage:
  python3 workflow/scripts/check_scope.py <role> [--base <commit>]
      Checks every change since <commit> (committed or not, plus untracked
      files), or every uncommitted change if no base is given. Exit 1 if a
      change is out of scope or HEAD has moved from <commit>. Record the base
      with `git rev-parse HEAD` before a role agent runs; check after it ends.
  python3 workflow/scripts/check_scope.py --hook
      PreToolUse hook for Claude Code (Edit, Write) and Codex (apply_patch).
      Reads the tool call from stdin and exits 2 to block a role agent's edit
      outside its scope. Calls from the main session or from agents without a
      role file are allowed.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = ROOT / "workflow" / "agents"
SCOPE_KEYS = ("writes", "never_writes")
FLAGS = re.IGNORECASE if os.name == "nt" else 0
PATCH_PATH = re.compile(
    r"^\s*\*\*\*\s*(?:Add File|Update File|Delete File|Move to)\s*:\s*(.+?)\s*$",
    re.MULTILINE,
)


def load_scope(role):
    """Return the role's scope, or None if the role has no file."""
    path = AGENTS_DIR / f"{role.replace('_', '-')}.md"
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path} has no front matter")
    scope = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        if key.strip() in SCOPE_KEYS:
            scope[key.strip()] = json.loads(value)
    missing = [key for key in SCOPE_KEYS if key not in scope]
    if missing:
        raise ValueError(f"{path} front matter lacks {', '.join(missing)}")
    return scope


def glob_to_regex(pattern):
    """Compile a scope pattern into a regular expression."""
    parts = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            parts.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            parts.append(".*")
            i += 2
        elif pattern[i] == "*":
            parts.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            parts.append("[^/]")
            i += 1
        else:
            parts.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(parts), FLAGS)


def matches(path, patterns):
    """Return whether the path matches any of the patterns."""
    return any(glob_to_regex(pattern).fullmatch(path) for pattern in patterns)


def in_scope(path, scope):
    """Check a repository-relative path that uses forward slashes."""
    return matches(path, scope["writes"]) and not matches(path, scope["never_writes"])


def relative_to_root(path, root=ROOT):
    """Return the path relative to the repository root, or None if outside it."""
    try:
        rel = os.path.relpath(
            os.path.normcase(os.path.abspath(path)), os.path.normcase(root)
        )
    except ValueError:  # another drive on Windows
        return None
    rel = rel.replace("\\", "/")
    return None if rel == ".." or rel.startswith("../") else rel


def git(root, *args):
    """Run git in root and return its output, raising if it fails."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8", errors="replace")


def changed_paths(base=None, root=ROOT):
    """Return changed paths, including both sides of a rename and untracked files."""
    paths = []
    if base:
        paths += [
            p
            for p in git(root, "diff", "--name-only", "--no-renames", "-z", base).split(
                "\0"
            )
            if p
        ]
    entries = git(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all"
    ).split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry:
            continue
        if not base or entry.startswith("??"):
            paths.append(entry[3:])
        if "R" in entry[:2] or "C" in entry[:2]:
            if not base:
                paths.append(entries[i])
            i += 1
    return sorted(set(paths))


def check_working_tree(role, base=None, root=ROOT):
    """Report out-of-scope changes and a moved HEAD, and return the exit code."""
    scope = load_scope(role)
    if scope is None:
        print(f"Unknown role '{role}': no workflow/agents/{role}.md", file=sys.stderr)
        return 2
    problems = [
        f"  {path}" for path in changed_paths(base, root) if not in_scope(path, scope)
    ]
    if (
        base
        and git(root, "rev-parse", "HEAD").strip()
        != git(root, "rev-parse", base).strip()
    ):
        problems.append(
            f"  HEAD has moved from {base}: "
            "role agents must not commit or switch branches"
        )
    if problems:
        print(f"Outside the {role} scope:")
        print("\n".join(problems))
        return 1
    print(f"All changes are within the {role} scope.")
    return 0


def check_hook_call():
    """Handle a hook call from stdin, returning 2 to block an out-of-scope edit."""
    try:
        event = json.load(sys.stdin)
    except ValueError:
        print("check_scope hook: stdin is not a JSON tool call", file=sys.stderr)
        return 1
    role = event.get("agent_type")
    if not role:
        return 0
    try:
        scope = load_scope(role)
    except ValueError as error:  # a broken role file blocks rather than allows
        print(f"Cannot read the {role} scope: {error}", file=sys.stderr)
        return 2
    if scope is None:
        return 0
    targets = edited_paths(event.get("tool_input") or {})
    if not targets:
        print(
            f"Blocked: cannot tell which files this {role} edit writes.",
            file=sys.stderr,
        )
        return 2
    for target in targets:
        if not os.path.isabs(target):
            target = os.path.join(event.get("cwd") or ROOT, target)
        rel = relative_to_root(target)
        if rel is None or not in_scope(rel, scope):
            print(
                f"Blocked: {role} may not write {rel or target}. It is outside "
                f"the scope in workflow/agents/{role.replace('_', '-')}.md. "
                "Do not work around this; report it in your handoff.",
                file=sys.stderr,
            )
            return 2
    return 0


def edited_paths(tool_input):
    """Return the paths a Claude Code edit or a Codex apply_patch would write."""
    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if target:
        return [target]
    patch = (
        tool_input.get("command")
        or tool_input.get("input")
        or tool_input.get("patch")
        or ""
    )
    return PATCH_PATH.findall(patch) if isinstance(patch, str) else []


def main(args):
    """Run the command in the usage above and return its exit code."""
    if args == ["--hook"]:
        return check_hook_call()
    if len(args) == 1 and not args[0].startswith("-"):
        return check_working_tree(args[0])
    if len(args) == 3 and not args[0].startswith("-") and args[1] == "--base":
        return check_working_tree(args[0], args[2])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
