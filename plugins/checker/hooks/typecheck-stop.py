#!/usr/bin/env python3
"""
Stop hook: Run type checking when Claude finishes editing Python files.
Only runs if backend/src/intric/**/*.py files were modified.
"""
import json
import os
import subprocess
import sys
from pathlib import Path


def get_changed_python_files(project_dir: str) -> list[str]:
    """Get Python files changed in worktree (staged + unstaged + untracked)."""
    files = []

    # Staged + unstaged changes
    result = subprocess.run(
        ["git", "-C", project_dir, "diff", "--name-only", "HEAD", "--",
         "backend/src/intric"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        files.extend(result.stdout.strip().split('\n'))

    # Untracked files
    result = subprocess.run(
        ["git", "-C", project_dir, "ls-files", "--others", "--exclude-standard",
         "backend/src/intric"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        files.extend(result.stdout.strip().split('\n'))

    # Filter to .py files only
    return [f for f in files if f and f.endswith('.py')]


def run_typecheck(project_dir: str) -> tuple[bool, str]:
    """Run typecheck_changed.sh and return (success, output)."""
    script = Path(project_dir) / "backend" / "scripts" / "typecheck_changed.sh"
    if not script.exists():
        return True, ""

    # Check for disable/warn-only modes
    if os.environ.get("TYPECHECK_DISABLE", "").lower() in ("1", "true"):
        return True, ""
    warn_only = os.environ.get("TYPECHECK_WARN_ONLY", "").lower() in ("1", "true")

    # Check if uv is available (soft-fail if missing)
    uv_check = subprocess.run(["which", "uv"], capture_output=True)
    if uv_check.returncode != 0:
        return True, "[typecheck] Warning: uv not found, skipping type check"

    # Check if pyright is available via uv (soft-fail if not installed)
    pyright_check = subprocess.run(
        ["uv", "run", "pyright", "--version"],
        cwd=Path(project_dir) / "backend",
        capture_output=True, text=True
    )
    if pyright_check.returncode != 0:
        return True, "[typecheck] Warning: pyright not installed, skipping type check"

    try:
        result = subprocess.run(
            ["bash", str(script)],
            cwd=Path(project_dir) / "backend",
            capture_output=True, text=True,
            timeout=120
        )
    except subprocess.TimeoutExpired:
        return True, "[typecheck] Warning: timed out after 120s"

    output = result.stderr if result.stderr else result.stdout

    # In warn-only mode, always return success but include output
    if warn_only:
        return True, output if result.returncode != 0 else ""

    return result.returncode == 0, output


def main():
    input_data = json.load(sys.stdin)

    # Prevent infinite loops - if stop hook already active, skip
    if input_data.get("stop_hook_active"):
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", input_data.get("cwd", os.getcwd()))

    # Check if any Python files in scope were changed
    changed_files = get_changed_python_files(project_dir)
    if not changed_files:
        sys.exit(0)  # No Python files changed, skip

    # Run type check
    success, output = run_typecheck(project_dir)

    if not success and output:
        # Limit output to top errors for readability
        lines = output.strip().split('\n')
        max_errors = 15
        truncated = len(lines) > max_errors
        display_output = '\n'.join(lines[:max_errors])
        if truncated:
            display_output += f"\n... and {len(lines) - max_errors} more errors"

        # Block and provide feedback to Claude
        result = {
            "decision": "block",
            "reason": (
                f"Type checking found errors in {len(changed_files)} file(s):\n\n"
                f"{display_output}\n\n"
                f"Fix these type errors. Run `/checker` to recheck."
            )
        }
        print(json.dumps(result))

    sys.exit(0)


if __name__ == "__main__":
    main()
