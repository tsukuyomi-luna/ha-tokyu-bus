"""Prevent accidental return to mutable action tags."""

import re
from pathlib import Path


def test_actions_use_full_commit_ids():
    workflow = Path(__file__).parents[1] / ".github/workflows/test.yaml"
    refs = re.findall(r"uses:\s+(\S+)", workflow.read_text())
    assert refs
    assert all(re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", ref) for ref in refs)


def test_ci_checks_format_lint_and_tests():
    workflow = (Path(__file__).parents[1] / ".github/workflows/test.yaml").read_text()
    for command in (
        "ruff format --check",
        "ruff check",
        "pytest",
        "npm ci",
        "format:check",
    ):
        assert command in workflow
