#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Reject tests where more than 30% of assertions are trivial.

Covers Section D Mechanism 4 anti-sycophancy clause: tests that assert `True`,
`x == x`, or `mock.return_value == mock.return_value` degrade the mutation
signal without catching real bugs. MuTAP (ScienceDirect 2024) shows coverage
alone is weakly correlated with bug detection; this validator is the cheap
first line of defense against trivially-passing tests produced under context
pressure.

Usage:

    uv run trivial_test_detector.py path/to/test_*.py ...
    uv run trivial_test_detector.py --threshold 0.2 tests/

Exit code 2 when any file exceeds the threshold.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


TRIVIAL_CONSTANTS = {True, False, None}


def _is_trivial(node: ast.expr) -> bool:
    """Return True if the assertion's expression is obviously tautological."""
    # assert <Constant>
    if isinstance(node, ast.Constant):
        return node.value in TRIVIAL_CONSTANTS or node.value == 1 or node.value == 0

    # assert x == x (same name/attr on both sides)
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        op = node.ops[0]
        if isinstance(op, (ast.Eq, ast.Is)):
            left = ast.dump(node.left, annotate_fields=False)
            right = ast.dump(node.comparators[0], annotate_fields=False)
            if left == right:
                return True

    # assert mock.return_value == <same attribute path>
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        left, right = node.left, node.comparators[0]
        if _same_attribute_chain(left, right):
            return True

    # assert True == True-equivalent (Constant compared to itself)
    return False


def _same_attribute_chain(a: ast.expr, b: ast.expr) -> bool:
    """True if a and b are the same attribute chain (e.g., x.y.z == x.y.z)."""
    def dump(n: ast.expr) -> str | None:
        if isinstance(n, ast.Name):
            return n.id
        if isinstance(n, ast.Attribute):
            base = dump(n.value)
            return f"{base}.{n.attr}" if base else None
        return None

    da, db = dump(a), dump(b)
    return bool(da and db and da == db)


def analyze(path: Path) -> tuple[int, int, list[tuple[int, str]]]:
    """Return (total_asserts, trivial_asserts, [(lineno, source)])."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"[trivial_test_detector] unable to read {path}: {exc}", file=sys.stderr)
        return 0, 0, []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        print(f"[trivial_test_detector] syntax error in {path}: {exc}", file=sys.stderr)
        return 0, 0, []

    total = 0
    trivial = 0
    offenders: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            total += 1
            if _is_trivial(node.test):
                trivial += 1
                offenders.append(
                    (node.lineno, ast.unparse(node).strip() if hasattr(ast, "unparse") else "<trivial>")
                )

    return total, trivial, offenders


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Test files or directories")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.30,
        help="Max fraction of trivial assertions allowed per file (default 0.30)",
    )
    parser.add_argument(
        "--min-asserts",
        type=int,
        default=3,
        help="Skip files with fewer than N assertions (default 3) — too small to judge",
    )
    args = parser.parse_args()

    files: list[Path] = []
    for p in args.paths:
        if p.is_dir():
            files.extend(p.rglob("test_*.py"))
            files.extend(p.rglob("*_test.py"))
        elif p.is_file():
            files.append(p)

    failed = False
    for f in files:
        total, trivial, offenders = analyze(f)
        if total < args.min_asserts:
            continue
        ratio = trivial / total
        if ratio > args.threshold:
            failed = True
            pct = ratio * 100
            print(
                f"[trivial_test_detector] {f}: {trivial}/{total} ({pct:.0f}%) assertions are trivial",
                file=sys.stderr,
            )
            for lineno, src in offenders[:10]:
                print(f"    {f}:{lineno}: {src}", file=sys.stderr)

    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
