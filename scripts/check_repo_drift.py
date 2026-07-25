#!/usr/bin/env python3
"""Fail when two SessionGuard checkouts do not point at the same revision.

The canonical checkout is intentionally supplied by the caller; no machine
specific path is embedded in the repository.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def git_head(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("canonical", type=Path)
    args = parser.parse_args()

    missing = [p for p in (args.checkout, args.canonical) if not p.is_dir()]
    if missing:
        print("Missing checkout(s): " + ", ".join(str(p) for p in missing), file=sys.stderr)
        return 2

    checkout_head = git_head(args.checkout)
    canonical_head = git_head(args.canonical)
    if checkout_head != canonical_head:
        print(f"DRIFT: checkout={checkout_head} canonical={canonical_head}", file=sys.stderr)
        return 1

    print(f"In sync at {checkout_head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
