"""Shared environment library for Eneo hooks (Python twin of env.sh).

Ports `find_repo_root()` + devcontainer detection from the legacy checker
plugin (plugins/checker/hooks/typecheck-stop.py) and adds the Decision 0.2
dual-mode execution wrapper so Python hooks have the same API as bash.

Import from a hook with:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent / "lib"))
    import env
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _is_eneo_candidate(name: str) -> bool:
    lowered = name.lower()
    if "eneo" not in lowered:
        return False
    return not any(part in lowered for part in ("db", "redis", "celery", "worker", "flow"))


def _preferred_eneo_container(names: list[str]) -> str | None:
    preferred_tokens = ("devcontainer", "backend", "app", "web", "api")
    for name in names:
        lowered = name.lower()
        if any(token in lowered for token in preferred_tokens) or lowered.endswith("eneo-1"):
            return name
    for name in names:
        if _is_eneo_candidate(name):
            return name
    return None


# --- Environment detection ---------------------------------------------------
def detect_env() -> str:
    """Return: in-container | host-with-docker | native | disabled."""
    mode = os.environ.get("ENEO_DEVCONTAINER_MODE", "").strip()
    if mode:
        return mode

    if (
        Path("/.dockerenv").exists()
        or os.environ.get("REMOTE_CONTAINERS")
        or os.environ.get("DEVCONTAINER")
    ):
        return "in-container"

    # Only consider host-with-docker if docker is installed AND an eneo
    # container name is running.
    try:
        ps = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if ps.returncode == 0 and _preferred_eneo_container(ps.stdout.splitlines()):
            return "host-with-docker"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "native"


_container_name_cache: str | None = None


def eneo_container_name() -> str | None:
    """Cached lookup of the first eneo-ish container currently running."""
    global _container_name_cache
    if _container_name_cache is not None:
        return _container_name_cache or None
    try:
        ps = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        selected = _preferred_eneo_container(ps.stdout.splitlines())
        if selected:
            _container_name_cache = selected
            return selected
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    _container_name_cache = ""
    return None


def eneo_exec(
    workdir: str,
    cmd: list[str],
    *,
    capture: bool = False,
    check: bool = False,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run *cmd* in the correct execution mode. workdir is relative to repo root.

    Soft-fails with returncode=0 when mode=disabled or host-with-docker cannot
    find a running container — matching the bash `eneo_exec` behavior.
    """
    mode = detect_env()
    root = find_repo_root()
    if mode == "disabled":
        return subprocess.CompletedProcess(cmd, 0, "", "")

    if mode in ("in-container", "native"):
        cwd = Path(root or ".") / workdir
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=capture,
            text=True,
            check=check,
            timeout=timeout,
        )

    if mode == "host-with-docker":
        container = eneo_container_name()
        if not container:
            # fail open on infra
            return subprocess.CompletedProcess(cmd, 0, "", "[eneo-env] no eneo devcontainer running; skipped\n")
        return subprocess.run(
            [
                "docker",
                "exec",
                "-w",
                f"/workspace/{workdir}",
                container,
                "bash",
                "-lc",
                'export PATH=/home/vscode/.local/bin:$PATH; "$@"',
                "bash",
                *cmd,
            ],
            capture_output=capture,
            text=True,
            check=check,
            timeout=timeout,
        )

    # Unknown mode — pass through unchanged
    return subprocess.run(
        cmd, capture_output=capture, text=True, check=check, timeout=timeout
    )


# --- Path translation --------------------------------------------------------
def host_to_container_path(p: str) -> str:
    root = find_repo_root() or ""
    return p.replace(root, "/workspace", 1) if root else p


def container_to_host_path(p: str) -> str:
    root = find_repo_root() or ""
    return p.replace("/workspace", root, 1) if root else p


# --- Repo-root detection (verbatim from checker/typecheck-stop.py lines 18–46)
def find_repo_root(start_dir: str | None = None) -> str | None:
    """Find the eneo repo root containing backend/src/intric."""
    start = Path(start_dir or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    # Try git root from start_dir first
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            git_root = Path(result.stdout.strip())
            if (git_root / "backend" / "src" / "intric").exists():
                return str(git_root)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check if start_dir itself has backend/src/intric
    if (start / "backend" / "src" / "intric").exists():
        return str(start)

    # Check common nested locations (eneo subdir, workspace)
    for subdir in ("eneo", "workspace"):
        candidate = start / subdir
        if (candidate / "backend" / "src" / "intric").exists():
            return str(candidate)

    # Check /workspace for devcontainer
    if Path("/workspace/backend/src/intric").exists():
        return "/workspace"

    return None


def get_changed_python_files(repo_root: str, scope: str = "backend/src/intric") -> list[str]:
    """Return staged + unstaged + untracked .py files inside *scope*."""
    files: list[str] = []
    try:
        diff = subprocess.run(
            ["git", "-C", repo_root, "diff", "--name-only", "HEAD", "--", scope],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if diff.returncode == 0:
            files.extend(diff.stdout.strip().splitlines())
        untracked = subprocess.run(
            ["git", "-C", repo_root, "ls-files", "--others", "--exclude-standard", scope],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if untracked.returncode == 0:
            files.extend(untracked.stdout.strip().splitlines())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    return [f for f in files if f and f.endswith(".py")]


# --- Phase-state helpers -----------------------------------------------------
def phase() -> str:
    """Return current phase: RED | GREEN | REFACTOR | FREE."""
    root = find_repo_root()
    if not root:
        return "FREE"
    phase_file = Path(root) / ".claude" / "state" / "phase"
    return phase_file.read_text().strip() if phase_file.exists() else "FREE"


def current_slug() -> str | None:
    root = find_repo_root()
    if not root:
        return None
    task = Path(root) / ".claude" / "state" / "current-task.json"
    if not task.exists():
        return None
    try:
        return json.loads(task.read_text()).get("slug")
    except (json.JSONDecodeError, OSError):
        return None


def env_report() -> dict[str, str | None]:
    return {
        "ENEO_DEVCONTAINER_MODE": os.environ.get("ENEO_DEVCONTAINER_MODE"),
        "detected_mode": detect_env(),
        "repo_root": find_repo_root(),
        "container": eneo_container_name(),
        "phase": phase(),
        "slug": current_slug(),
    }


if __name__ == "__main__":
    print(json.dumps(env_report(), indent=2))
