#!/usr/bin/env python3
"""Stop hook: run pyright when Claude finishes editing Python files under
backend/src/intric/. Ported verbatim from plugins/checker/hooks/typecheck-stop.py
but routed through the shared env library so behavior is consistent with the
rest of the eneo-standards hooks.

Works in multiple environments via env.detect_env():
- Normal clone: ~/projects/eneo/backend/src/intric
- Devcontainer: /workspace/backend/src/intric
- Nested setup: ~/eneo/eneo/backend/src/intric
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# Make the shared env library importable (runtime path)
sys.path.insert(0, str(Path(__file__).parent / "lib"))
import env  # type: ignore[import-not-found]  # noqa: E402


def run_typecheck(repo_root: str) -> tuple[bool, str]:
    """Run typecheck_changed.sh and return (success, output)."""
    script = Path(repo_root) / "backend" / "scripts" / "typecheck_changed.sh"
    if not script.exists():
        return True, ""

    if os.environ.get("TYPECHECK_DISABLE", "").lower() in ("1", "true"):
        return True, ""
    warn_only = os.environ.get("TYPECHECK_WARN_ONLY", "").lower() in ("1", "true")

    # Soft-fail if uv or pyright are unavailable in the selected environment
    mode = env.detect_env()
    uv_check = env.eneo_exec("backend", ["uv", "--version"], capture=True)
    if uv_check.returncode != 0:
        return True, f"[typecheck] Warning: uv not available in mode={mode}; skipping"

    pyright_check = env.eneo_exec(
        "backend", ["uv", "run", "pyright", "--version"], capture=True, timeout=20
    )
    if pyright_check.returncode != 0:
        return True, f"[typecheck] Warning: pyright not installed in mode={mode}; skipping"

    try:
        # typecheck_changed.sh lives in the Eneo repo and is the team's
        # canonical entry point — call it through eneo_exec to respect mode.
        result = env.eneo_exec(
            "backend",
            ["bash", str(script)],
            capture=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return True, "[typecheck] Warning: timed out after 120s"

    output = result.stderr or result.stdout or ""

    if warn_only:
        return True, output if result.returncode != 0 else ""

    return result.returncode == 0, output


def main() -> int:
    input_data = json.load(sys.stdin)

    # Avoid infinite loops if a Stop hook fires from inside another Stop hook
    if input_data.get("stop_hook_active"):
        return 0

    repo_root = env.find_repo_root(input_data.get("cwd"))
    if not repo_root:
        return 0  # not in an eneo repo

    changed = env.get_changed_python_files(repo_root)
    if not changed:
        return 0

    success, output = run_typecheck(repo_root)
    if not success and output:
        lines = output.strip().splitlines()
        max_errors = 15
        truncated = len(lines) > max_errors
        display = "\n".join(lines[:max_errors])
        if truncated:
            display += f"\n... and {len(lines) - max_errors} more errors"

        print(json.dumps({
            "decision": "block",
            "reason": (
                f"✗ Type checking failed in {len(changed)} file(s).\n"
                f"  Rule: pyright strict ratchet (.claude/rules/eneo-context.md#pyright-strict).\n"
                f"  Fix:  resolve the errors below, then re-run '/eneo-verify' or /checker.\n\n"
                f"{display}"
            ),
        }))

    return 0


if __name__ == "__main__":
    sys.exit(main())
