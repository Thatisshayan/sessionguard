"""Unit tests for scripts/check_repo_drift.py (Revival 1.3, A3).

The drift script is the mechanism that should have caught finding #13 (two
checkouts six phases apart, both labelled "in sync"). These tests pin its
contract on a temp checkouts pair so no real SessionGuard path is required.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_repo_drift.py"


def _git(repo: Path, *args: str) -> str:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e",
           "GIT_AUTHOR_DATE": "2026-07-25T00:00:00",
           "GIT_COMMITTER_DATE": "2026-07-25T00:00:00"}
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True, env=env, check=True)
    return r.stdout.strip()


@pytest.fixture
def two_repos(tmp_path: Path):
    """Two throwaway git repos so the drift script can be exercised off-line."""
    a = tmp_path / "checkout_a"
    b = tmp_path / "checkout_b"
    for repo in (a, b):
        repo.mkdir()
        _git(repo, "init", "-q")
        (repo / "README.md").write_text("# SessionGuard\n")
        _git(repo, "add", "README.md")
        _git(repo, "commit", "-q", "-m", "init")
    return a, b


def test_in_sync_repos_exit_zero(two_repos):
    a, b = two_repos
    r = subprocess.run([sys.executable, str(SCRIPT), str(a), str(b)],
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "In sync" in r.stdout


def test_drifted_repos_exit_nonzero(two_repos):
    a, b = two_repos
    # Advance one checkout past the other.
    (a / "CHANGE.md").write_text("change\n")
    _git(a, "add", "CHANGE.md")
    _git(a, "commit", "-q", "-m", "advance")
    r = subprocess.run([sys.executable, str(SCRIPT), str(a), str(b)],
                       capture_output=True, text=True)
    assert r.returncode == 1
    assert "DRIFT" in r.stderr


def test_missing_checkout_exit_nonzero(tmp_path):
    a = tmp_path / "exists"
    a.mkdir()
    _git(a, "init", "-q")
    (a / "README.md").write_text("# x\n")
    _git(a, "add", "README.md")
    _git(a, "commit", "-q", "-m", "init")
    missing = tmp_path / "does_not_exist"
    r = subprocess.run([sys.executable, str(SCRIPT), str(a), str(missing)],
                       capture_output=True, text=True)
    assert r.returncode == 2
    assert "Missing checkout" in r.stderr
