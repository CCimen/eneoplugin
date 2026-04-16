#!/usr/bin/env bash
# Shared env library for Eneo hooks.
# Sourced by every hook: detect_env + eneo_exec + find_repo_root.
# Follows playbook Decision 0.2 (devcontainer dual-mode).
# Soft-fails on infrastructure errors; hard-fails only on policy violations.

set -euo pipefail

# --- Environment detection ----------------------------------------------------
# ENEO_DEVCONTAINER_MODE: in-container | host-with-docker | native | disabled
eneo_container_candidates() {
  docker ps --format '{{.Names}}' 2>/dev/null \
    | awk '
      /eneo/ && $0 !~ /(db|redis|celery|worker|flow)/ {
        print
      }
    '
}

_eneo_preferred_container() {
  eneo_container_candidates \
    | grep -E '(devcontainer|backend|app|web|api|(^|[-_])eneo[-_]1$|(^|[-_])eneo[-_][0-9]+$|[-_]eneo[-_]1$)' \
    | head -1
}

detect_env() {
  if [[ -n "${ENEO_DEVCONTAINER_MODE:-}" ]]; then
    echo "$ENEO_DEVCONTAINER_MODE"
    return
  fi
  if [[ -f /.dockerenv ]] || [[ -n "${REMOTE_CONTAINERS:-}" ]] || [[ -n "${DEVCONTAINER:-}" ]]; then
    echo "in-container"
    return
  fi
  if command -v docker >/dev/null 2>&1 && \
     { [[ -n "$(_eneo_preferred_container)" ]] || [[ -n "$(eneo_container_candidates | head -1)" ]]; }; then
    echo "host-with-docker"
    return
  fi
  echo "native"
}

ENEO_CONTAINER_NAME_CACHE=""
eneo_container_name() {
  if [[ -n "$ENEO_CONTAINER_NAME_CACHE" ]]; then
    echo "$ENEO_CONTAINER_NAME_CACHE"
    return
  fi
  ENEO_CONTAINER_NAME_CACHE=$(_eneo_preferred_container || true)
  if [[ -z "$ENEO_CONTAINER_NAME_CACHE" ]]; then
    ENEO_CONTAINER_NAME_CACHE=$(eneo_container_candidates | head -1 || true)
  fi
  echo "$ENEO_CONTAINER_NAME_CACHE"
}

# --- Command wrapper ----------------------------------------------------------
# Usage: eneo_exec <workdir-relative-to-repo-root> <cmd> [args...]
# Returns the exit code of the wrapped command, or 0 if mode=disabled or
# host-with-docker fails to find a running container (fail open on infra).
eneo_exec() {
  local workdir="$1"
  shift
  local mode
  mode=$(detect_env)
  local root
  root=$(eneo_repo_root)
  case "$mode" in
    disabled)
      return 0
      ;;
    in-container|native)
      ( cd "${root}/${workdir}" && "$@" )
      ;;
    host-with-docker)
      local container
      container=$(eneo_container_name)
      if [[ -z "$container" ]]; then
        echo "[eneo-env] no eneo devcontainer running; skipping: $*" >&2
        return 0  # fail open
      fi
      docker exec -w "/workspace/${workdir}" "$container" \
        bash -lc 'export PATH=/home/vscode/.local/bin:$PATH; "$@"' bash "$@"
      ;;
  esac
}

# --- Path translation ---------------------------------------------------------
host_to_container_path() {
  local p="$1"
  local root
  root=$(eneo_repo_root)
  echo "${p/$root/\/workspace}"
}

container_to_host_path() {
  local p="$1"
  local root
  root=$(eneo_repo_root)
  echo "${p/\/workspace/$root}"
}

# --- Repo-root detection (ported from plugins/checker/hooks/typecheck-stop.py)
# Handles: normal clone, nested ~/eneo/eneo/, devcontainer /workspace,
# and CLAUDE_PROJECT_DIR fallback.
eneo_repo_root() {
  local start="${CLAUDE_PROJECT_DIR:-$(pwd)}"

  # 1. git rev-parse from start
  local git_root
  if git_root=$(git -C "$start" rev-parse --show-toplevel 2>/dev/null); then
    if [[ -d "$git_root/backend/src/intric" ]]; then
      echo "$git_root"
      return
    fi
  fi

  # 2. start itself contains backend/src/intric
  if [[ -d "$start/backend/src/intric" ]]; then
    echo "$start"
    return
  fi

  # 3. nested eneo/ or workspace/ subdir
  for sub in eneo workspace; do
    if [[ -d "$start/$sub/backend/src/intric" ]]; then
      echo "$start/$sub"
      return
    fi
  done

  # 4. /workspace devcontainer layout
  if [[ -d /workspace/backend/src/intric ]]; then
    echo /workspace
    return
  fi

  # 5. Fall back to start — callers can check for existence
  echo "$start"
}

# --- Phase-state helpers ------------------------------------------------------
# Returns RED | GREEN | REFACTOR | FREE (default).
eneo_phase() {
  local root
  root=$(eneo_repo_root)
  cat "$root/.claude/state/phase" 2>/dev/null || echo "FREE"
}

eneo_current_slug() {
  local root
  root=$(eneo_repo_root)
  local file="$root/.claude/state/current-task.json"
  if [[ -f "$file" ]]; then
    # Parse JSON "slug" without requiring jq (fail soft)
    if command -v jq >/dev/null 2>&1; then
      jq -r '.slug // empty' "$file" 2>/dev/null || true
    else
      sed -n 's/.*"slug"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$file" | head -1
    fi
  fi
}

# --- Debug introspection ------------------------------------------------------
eneo_env_report() {
  echo "ENEO_DEVCONTAINER_MODE=${ENEO_DEVCONTAINER_MODE:-<unset>}"
  echo "detected_mode=$(detect_env)"
  echo "repo_root=$(eneo_repo_root)"
  echo "container=$(eneo_container_name)"
  echo "phase=$(eneo_phase)"
  echo "slug=$(eneo_current_slug)"
}
