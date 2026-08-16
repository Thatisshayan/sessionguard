#!/usr/bin/env python3
"""
scripts/generate_changelog.py
------------------------------
Generates a structured CHANGELOG.md file from conventional commit history.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def get_git_commits():
    try:
        out = subprocess.check_output(
            ["git", "log", "--pretty=format:%h|%s|%an|%ad", "--date=short", "-n", "50"],
            text=True,
            cwd=str(ROOT)
        )
        return out.splitlines()
    except Exception as e:
        print(f"[Changelog] Error fetching git log: {e}")
        return []

def parse_commits(commit_lines):
    categories = {
        "Features": [],
        "Bug Fixes": [],
        "Documentation": [],
        "Refactoring & Performance": [],
        "Maintenance & Chores": [],
    }

    for line in commit_lines:
        parts = line.split("|")
        if len(parts) < 4:
            continue
        commit_hash, subject, author, date = parts
        
        entry = f"- `{commit_hash}` {subject} ({author}, {date})"

        if subject.startswith("feat"):
            categories["Features"].append(entry)
        elif subject.startswith("fix"):
            categories["Bug Fixes"].append(entry)
        elif subject.startswith("docs"):
            categories["Documentation"].append(entry)
        elif subject.startswith("refactor") or subject.startswith("perf"):
            categories["Refactoring & Performance"].append(entry)
        else:
            categories["Maintenance & Chores"].append(entry)

    return categories

def generate_changelog_md():
    lines = get_git_commits()
    categories = parse_commits(lines)

    content = ["# SessionGuard Application Changelog\n", "Automated conventional commit release log.\n"]

    for cat_name, entries in categories.items():
        if entries:
            content.append(f"## {cat_name}\n")
            content.extend([f"{e}\n" for e in entries])
            content.append("\n")

    changelog_path = ROOT / "CHANGELOG.md"
    changelog_path.write_text("".join(content), encoding="utf-8")
    print(f"[Changelog] Successfully generated {changelog_path}")

if __name__ == "__main__":
    generate_changelog_md()
