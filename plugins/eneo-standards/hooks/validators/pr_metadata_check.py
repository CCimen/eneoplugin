#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Enforce required PR metadata on /eneo-ship output.

Per Section F /eneo-ship: PR body MUST include tenancy:*, audit:*, PRD:#<n>,
Phase: <N>, and a verify-work evidence section. The Stop-hook invokes this
validator with the new PR number; exit 2 fails the ship.

Reads the PR body via `gh pr view <n> --json body`.

Usage:

    uv run pr_metadata_check.py --pr 1234
    uv run pr_metadata_check.py --body-file /tmp/pr-body.md   # for testing
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_PATTERNS: list[tuple[str, str]] = [
    (
        "tenancy tag",
        r"(?i)\btenancy\b[^A-Za-z0-9\n]{0,6}(isolated|shared|cross|tenant-scoped|none)",
    ),
    (
        "audit tag",
        r"(?i)\baudit\b[^A-Za-z0-9\n]{0,6}(none|appends|schema|appends-to-audit|schema-change)",
    ),
    ("PRD link", r"(?i)\bPRD\b[^#\n]{0,6}#\d+"),
    ("phase number", r"(?i)\bPhase\b[^0-9\n]{0,6}\d+"),
    ("verify evidence section",
                    r"(?mi)^##\s+(verify(-work)?|evidence|verify evidence)"),
]


def fetch_body(pr: str) -> str:
    """Fetch PR body via gh CLI."""
    result = subprocess.run(
        ["gh", "pr", "view", pr, "--json", "body"],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if result.returncode != 0:
        print(
            f"[pr_metadata_check] gh pr view failed: {result.stderr.strip()}",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        return json.loads(result.stdout)["body"] or ""
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"[pr_metadata_check] unable to parse gh output: {exc}", file=sys.stderr)
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pr", help="PR number to fetch via gh")
    group.add_argument("--body-file", type=Path, help="Local file with PR body (testing)")
    args = parser.parse_args()

    if args.pr:
        body = fetch_body(args.pr)
    else:
        body = args.body_file.read_text(encoding="utf-8")

    missing: list[str] = []
    for label, pattern in REQUIRED_PATTERNS:
        if not re.search(pattern, body):
            missing.append(f"{label} (regex: {pattern})")

    if missing:
        print("[pr_metadata_check] PR body is missing required metadata:", file=sys.stderr)
        for m in missing:
            print(f"  • {m}", file=sys.stderr)
        print(
            "\nAdd the missing fields to the PR body. The ship cannot proceed "
            "without them — see /eneo-ship documentation.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
