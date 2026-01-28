#!/usr/bin/env python3
"""
MCP server for per-file Pyright type checking with ratcheting support.

Provides a typecheck tool that Claude can call immediately after editing files
to get instant feedback on type errors without waiting for the Stop hook.

Works in multiple environments:
- Normal clone: ~/projects/eneo/backend/src/intric
- Devcontainer: /workspace/backend/src/intric
- Nested setup: ~/eneo/eneo/backend/src/intric
"""
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from pydantic import BaseModel, Field


class TypecheckError(BaseModel):
    """A single type error."""

    file: str
    line: int
    column: int
    severity: str
    rule: str | None
    message: str


class TypecheckResult(BaseModel):
    """Result of type checking."""

    success: bool
    files_checked: list[str]
    error_count: int
    errors: list[TypecheckError]
    summary: str


mcp = FastMCP(
    name="checker",
    version="1.0.0",
    instructions="""Type checking tool for eneo Python backend.

Use this tool PROACTIVELY after editing Python files in backend/src/intric/ to catch
type errors immediately. Don't wait for the Stop hook - check files as you edit them.

The tool respects the ratcheting baseline, so you'll only see NEW errors you introduced,
not legacy errors that existed before.""",
)


def find_repo_root(start_dir: str) -> str | None:
    """Find the eneo repo root containing backend/src/intric."""
    start = Path(start_dir)

    # Try git root from start_dir first
    result = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        git_root = Path(result.stdout.strip())
        if (git_root / "backend" / "src" / "intric").exists():
            return str(git_root)

    # Check if start_dir itself has backend/src/intric
    if (start / "backend" / "src" / "intric").exists():
        return str(start)

    # Check common nested locations (eneo subdir, workspace)
    for subdir in ["eneo", "workspace"]:
        candidate = start / subdir
        if (candidate / "backend" / "src" / "intric").exists():
            return str(candidate)

    # Check /workspace for devcontainer
    if Path("/workspace/backend/src/intric").exists():
        return "/workspace"

    return None


def is_new_file(file_path: str, repo_root: str) -> bool:
    """Check if file is new (untracked or staged as new)."""
    # Normalize to relative path from repo root
    rel_path = file_path
    if file_path.startswith(repo_root):
        rel_path = os.path.relpath(file_path, repo_root)

    # Add backend/ prefix if needed for git commands
    if not rel_path.startswith("backend/"):
        rel_path = f"backend/{rel_path}"

    # Check if untracked
    result = subprocess.run(
        ["git", "-C", repo_root, "ls-files", "--others", "--exclude-standard", rel_path],
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        return True

    # Check if staged as added
    result = subprocess.run(
        [
            "git",
            "-C",
            repo_root,
            "diff",
            "--name-only",
            "--diff-filter=A",
            "--cached",
            "--",
            rel_path,
        ],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def normalize_path(path: str, backend_dir: str) -> str:
    """Normalize file path to be relative to backend/."""
    path = path.replace("\\", "/")

    # If absolute, make relative to backend
    if path.startswith("/"):
        if "/backend/" in path:
            path = path.split("/backend/")[-1]
        elif backend_dir and path.startswith(backend_dir):
            path = os.path.relpath(path, backend_dir)

    # Remove leading backend/ if present
    if path.startswith("backend/"):
        path = path[8:]

    # Remove leading ./
    path = path.lstrip("./")

    return path


def load_baseline(baseline_path: Path) -> set[tuple]:
    """Load baseline and return set of diagnostic keys."""
    if not baseline_path.exists():
        return set()

    with open(baseline_path) as f:
        baseline = json.load(f)

    keys = set()
    for diag in baseline.get("generalDiagnostics", []):
        # Position-independent key (matches RATCHET_IGNORE_RANGE=1 behavior)
        key = (
            normalize_path(diag.get("file", ""), ""),
            diag.get("rule", ""),
            diag.get("message", ""),
            diag.get("severity", ""),
        )
        keys.add(key)

    return keys


def parse_pyright_output(
    output: dict,
    baseline_keys: set[tuple],
    files_filter: set[str] | None = None,
    is_strict: bool = False,
) -> list[TypecheckError]:
    """Parse pyright JSON output into structured errors, filtering by baseline."""
    errors = []

    for diag in output.get("generalDiagnostics", []):
        file_path = diag.get("file", "")
        normalized = normalize_path(file_path, "")

        # Filter to requested files if specified
        if files_filter:
            matches = any(
                normalized.endswith(f) or f.endswith(normalized) or normalized == f
                for f in files_filter
            )
            if not matches:
                continue

        # For existing files (not strict), filter out baseline errors
        if not is_strict:
            key = (
                normalized,
                diag.get("rule", ""),
                diag.get("message", ""),
                diag.get("severity", ""),
            )
            if key in baseline_keys:
                continue  # Skip baseline error

        # Only include errors (not warnings) for consistency with CI
        if diag.get("severity") != "error":
            continue

        range_info = diag.get("range", {})
        start = range_info.get("start", {})

        errors.append(
            TypecheckError(
                file=normalized,
                line=(start.get("line", 0) or 0) + 1,  # Convert to 1-indexed
                column=(start.get("character", 0) or 0) + 1,
                severity=diag.get("severity", "error"),
                rule=diag.get("rule"),
                message=diag.get("message", ""),
            )
        )

    return errors


def run_pyright(
    files: list[str],
    backend_dir: str,
    config: str | None = None,
) -> dict | None:
    """Run pyright on files and return JSON output."""
    cmd = ["uv", "run", "pyright", "--outputjson"]
    if config:
        cmd.extend(["--project", config])
    cmd.extend(files)

    try:
        result = subprocess.run(
            cmd,
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.stdout:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        pass

    return None


@mcp.tool()
def typecheck(
    files: list[str] = Field(
        default_factory=list,
        description="Files to check (relative to backend/, e.g. 'src/intric/files/file_service.py'). Empty = all changed files.",
    ),
) -> TypecheckResult:
    """
    Run Pyright type checking on specific Python files.

    Uses ratcheting baseline for existing files (only shows NEW errors you introduced).
    Uses strict mode for new/untracked files.

    Call this PROACTIVELY after editing Python files in backend/src/intric/
    to get immediate feedback. Don't wait for the Stop hook.

    Examples:
    - typecheck(files=["src/intric/files/file_service.py"]) - check one file
    - typecheck(files=[]) - check all changed files
    """
    # Find repo root
    cwd = os.getcwd()
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", cwd)
    repo_root = find_repo_root(project_dir)

    if not repo_root:
        return TypecheckResult(
            success=True,
            files_checked=[],
            error_count=0,
            errors=[],
            summary="Not in eneo repository (backend/src/intric not found)",
        )

    backend_dir = str(Path(repo_root) / "backend")
    baseline_path = Path(backend_dir) / ".pyright-baseline.json"
    strict_config = Path(backend_dir) / "pyrightconfig.strict.json"

    # Check if uv is available
    uv_check = subprocess.run(["which", "uv"], capture_output=True)
    if uv_check.returncode != 0:
        return TypecheckResult(
            success=True,
            files_checked=[],
            error_count=0,
            errors=[],
            summary="uv not found, cannot run type checking",
        )

    # If no files specified, get all changed files
    if not files:
        # Staged + unstaged changes
        result = subprocess.run(
            [
                "git",
                "-C",
                repo_root,
                "diff",
                "--name-only",
                "HEAD",
                "--",
                "backend/src/intric",
            ],
            capture_output=True,
            text=True,
        )
        changed = [f for f in result.stdout.strip().split("\n") if f.endswith(".py")]

        # Untracked files
        result = subprocess.run(
            [
                "git",
                "-C",
                repo_root,
                "ls-files",
                "--others",
                "--exclude-standard",
                "backend/src/intric",
            ],
            capture_output=True,
            text=True,
        )
        untracked = [f for f in result.stdout.strip().split("\n") if f.endswith(".py")]

        # Combine and normalize
        all_files = list(set(changed + untracked))
        files = [normalize_path(f, backend_dir) for f in all_files if f]

    if not files:
        return TypecheckResult(
            success=True,
            files_checked=[],
            error_count=0,
            errors=[],
            summary="No Python files to check",
        )

    # Normalize input paths
    normalized_files = []
    for f in files:
        norm = normalize_path(f, backend_dir)
        # Ensure it's in src/intric scope
        if norm.startswith("src/intric/") or "src/intric/" in norm:
            normalized_files.append(norm)

    if not normalized_files:
        return TypecheckResult(
            success=True,
            files_checked=files,
            error_count=0,
            errors=[],
            summary="No files in backend/src/intric/ scope",
        )

    # Separate new vs existing files
    new_files = []
    existing_files = []

    for f in normalized_files:
        if is_new_file(f, repo_root):
            new_files.append(f)
        else:
            existing_files.append(f)

    # Load baseline for existing files
    baseline_keys = load_baseline(baseline_path)

    all_errors: list[TypecheckError] = []
    files_checked = []

    # Check new files with strict config
    if new_files:
        files_checked.extend(new_files)
        if strict_config.exists():
            output = run_pyright(new_files, backend_dir, str(strict_config))
        else:
            output = run_pyright(new_files, backend_dir)

        if output:
            file_set = set(new_files)
            errors = parse_pyright_output(output, set(), file_set, is_strict=True)
            all_errors.extend(errors)

    # Check existing files with baseline ratcheting
    if existing_files:
        files_checked.extend(existing_files)
        output = run_pyright(existing_files, backend_dir)

        if output:
            file_set = set(existing_files)
            errors = parse_pyright_output(output, baseline_keys, file_set, is_strict=False)
            all_errors.extend(errors)

    # Build result
    error_count = len(all_errors)
    if error_count == 0:
        summary = f"No type errors in {len(files_checked)} file(s)"
    else:
        summary = f"{error_count} type error(s) in {len(files_checked)} file(s)"

    return TypecheckResult(
        success=error_count == 0,
        files_checked=files_checked,
        error_count=error_count,
        errors=all_errors,
        summary=summary,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
