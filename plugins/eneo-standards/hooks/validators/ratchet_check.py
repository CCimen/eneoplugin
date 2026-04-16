#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Coverage + mutation ratchet check, invoked by stop-ratchet.sh.

Section D Mechanism 4: stack coverage (weak floor) with mutation testing
(true signal). Per-file floors live in:
    .claude/ratchet/coverage.json   → {file: min_line_coverage_percent}
    .claude/ratchet/mutation.json   → {file-or-module: min_mutation_score_percent}

This validator compares committed ratchet baselines against current artifacts.
By default it reads repo-root `coverage.json` and `mutmut.json`, or explicit
paths passed via `--current-coverage` / `--current-mutation`. It can also
bootstrap empty baseline files with `--init`.

Exit 0 = no regressions. Exit 2 = regression (printed to stderr).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_ratchet(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[ratchet_check] {path} is not valid JSON", file=sys.stderr)
        return {}
    return {str(k): float(v) for k, v in data.items() if isinstance(v, (int, float))}


def _current_coverage(produced: Path) -> dict[str, float]:
    if not produced.exists():
        return {}
    try:
        data = json.loads(produced.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    files = data.get("files", {})
    return {
        path: float(info["summary"].get("percent_covered", 0.0))
        for path, info in files.items()
        if isinstance(info, dict) and "summary" in info
    }


def _current_mutation(produced: Path) -> dict[str, float]:
    if not produced.exists():
        return {}
    try:
        data = json.loads(produced.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict) and "files" in data:
        return {
            path: float(info.get("score", 0.0))
            for path, info in data["files"].items()
        }
    return {}


def _check(label: str, baseline: dict[str, float], current: dict[str, float]) -> list[str]:
    """Return list of regression messages."""
    regressions: list[str] = []
    for path, floor in baseline.items():
        if path not in current:
            # File was removed or not in this run — do not fail. (Covers the
            # common case where a commit deletes a file; next ratchet update
            # will drop it from the baseline.)
            continue
        actual = current[path]
        if actual + 0.01 < floor:  # small tolerance for floating-point drift
            regressions.append(
                f"{label} regression: {path} — floor {floor:.1f}%, actual {actual:.1f}%"
            )
    return regressions


def _init(repo_root: Path, coverage_path: Path | None, mutation_path: Path | None) -> None:
    """Create empty ratchet files so stop-ratchet.sh has a baseline to compare."""
    paths = [
        coverage_path or (repo_root / ".claude" / "ratchet" / "coverage.json"),
        mutation_path or (repo_root / ".claude" / "ratchet" / "mutation.json"),
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("{}\n", encoding="utf-8")
            print(f"[ratchet_check] initialized empty baseline: {path}")
        else:
            print(f"[ratchet_check] exists, leaving untouched: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path)
    parser.add_argument("--mutation", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--current-coverage", type=Path)
    parser.add_argument("--current-mutation", type=Path)
    parser.add_argument(
        "--allow-missing-current",
        action="store_true",
        help="Soft-pass when a baseline exists but the current coverage/mutation artifact is missing.",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Create empty coverage.json and mutation.json baselines under .claude/ratchet/. "
             "Run once per clone to quiet 'ratchet file missing' diagnostics.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    if args.init:
        _init(repo_root, args.coverage, args.mutation)
        return 0

    if args.coverage is None or args.mutation is None:
        parser.error("--coverage and --mutation are required unless --init is passed")

    cov_floor = _load_ratchet(args.coverage)
    mut_floor = _load_ratchet(args.mutation)
    current_coverage_path = (args.current_coverage or (repo_root / "coverage.json")).resolve()
    current_mutation_path = (args.current_mutation or (repo_root / "mutmut.json")).resolve()

    regressions: list[str] = []
    missing_inputs: list[str] = []
    if cov_floor:
        current = _current_coverage(current_coverage_path)
        if current:
            regressions.extend(_check("coverage", cov_floor, current))
        elif not args.allow_missing_current:
            missing_inputs.append(str(current_coverage_path))
    if mut_floor:
        current = _current_mutation(current_mutation_path)
        if current:
            regressions.extend(_check("mutation", mut_floor, current))
        elif not args.allow_missing_current:
            missing_inputs.append(str(current_mutation_path))

    if missing_inputs:
        print("[ratchet_check] current ratchet artifacts are missing:", file=sys.stderr)
        for path in missing_inputs:
            print(f"  • {path}", file=sys.stderr)
        print(
            "\nGenerate the current coverage/mutation artifacts before relying on the ratchet.",
            file=sys.stderr,
        )
        return 2

    if regressions:
        print("[ratchet_check] regressions detected:", file=sys.stderr)
        for r in regressions:
            print(f"  • {r}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
