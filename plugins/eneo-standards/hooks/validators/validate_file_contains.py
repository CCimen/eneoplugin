#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Assert that a file contains every required string.

Used by disler-style embedded Stop-hook validators on slash commands to ensure
generated artifacts (PRDs, plans, phase files, SPECs) include required sections.

Exit code 2 (not 1) on failure — Claude Code swallows exit 1 silently per
GH issue anthropics/claude-code#21988. Stderr is surfaced back to the model
so it can re-loop and add the missing section.

Example:

    uv run validate_file_contains.py \\
      --file .claude/plans/revoke-api-keys.md \\
      --contains '## Phase 1: Tracer Bullet' \\
      --contains '## Out of scope' \\
      --contains 'PRD:' \\
      --contains 'Wave plan:'
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path, help="File to check")
    parser.add_argument(
        "--contains",
        action="append",
        default=[],
        metavar="STRING",
        help="Required substring (repeatable)",
    )
    parser.add_argument(
        "--regex",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Required regex pattern (repeatable)",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=None,
        help="If set, fail when the file exceeds this many lines (e.g., CLAUDE.md cap)",
    )
    args = parser.parse_args()

    path: Path = args.file
    if not path.exists():
        print(f"[validate_file_contains] missing file: {path}", file=sys.stderr)
        return 2

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[validate_file_contains] unable to read {path}: {exc}", file=sys.stderr)
        return 2

    missing: list[str] = []
    for needle in args.contains:
        if needle not in content:
            missing.append(needle)

    import re

    missing_patterns: list[str] = []
    for pattern in args.regex:
        if not re.search(pattern, content, re.MULTILINE):
            missing_patterns.append(pattern)

    length_error: str | None = None
    if args.max_lines is not None:
        lines = content.count("\n") + (0 if content.endswith("\n") else 1)
        if lines > args.max_lines:
            length_error = (
                f"{path} has {lines} lines but max-lines is {args.max_lines}"
            )

    if missing or missing_patterns or length_error:
        print(f"[validate_file_contains] {path} failed validation:", file=sys.stderr)
        for m in missing:
            print(f"  missing substring: {m!r}", file=sys.stderr)
        for m in missing_patterns:
            print(f"  missing pattern:   /{m}/m", file=sys.stderr)
        if length_error:
            print(f"  {length_error}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
