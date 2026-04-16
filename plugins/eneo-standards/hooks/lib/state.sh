#!/usr/bin/env bash
# Shared state-management helpers for Eneo hooks and commands.
# Every writer of .claude/state/current-task.json goes through eneo_task_update
# so the atomic mktemp+mv pattern + schema validation live in exactly one place
# and we cannot drift (e.g. one hook writing wave_status as an array, another
# as an object — reviewer #5).
#
# Source after lib/env.sh:
#   source "${BASH_SOURCE%/*}/lib/env.sh"
#   source "${BASH_SOURCE%/*}/lib/state.sh"

set -uo pipefail

# Paths (functions so they re-resolve when CLAUDE_PROJECT_DIR changes between calls).
eneo_task_file()  { echo "$(eneo_repo_root)/.claude/state/current-task.json"; }
eneo_phase_file() { echo "$(eneo_repo_root)/.claude/state/phase"; }
eneo_wave_file()  { echo "$(eneo_repo_root)/.claude/state/wave.json"; }
eneo_state_lock_root() { echo "$(eneo_repo_root)/.claude/state/.locks"; }
eneo_lock_ttl_seconds() { echo 30; }

eneo_file_mtime() {
  local path="$1"
  if stat -f %m "$path" >/dev/null 2>&1; then
    stat -f %m "$path"
  else
    stat -c %Y "$path"
  fi
}

# --- Lock helpers -------------------------------------------------------------
# Use a directory lock instead of flock so this works on the host, inside the
# devcontainer, and on macOS without extra tooling.
eneo_acquire_lock() {
  local name="$1"
  local lock_root lock_dir attempts
  lock_root=$(eneo_state_lock_root)
  mkdir -p "$lock_root" 2>/dev/null || true
  lock_dir="$lock_root/${name}.lock"
  attempts=0
  while ! mkdir "$lock_dir" 2>/dev/null; do
    attempts=$((attempts + 1))
    local now owner_path owner_mtime ttl
    owner_path="$lock_dir/owner"
    ttl=$(eneo_lock_ttl_seconds)
    now=$(date +%s)
    owner_mtime=$(eneo_file_mtime "$owner_path" 2>/dev/null || eneo_file_mtime "$lock_dir" 2>/dev/null || echo 0)
    if [[ -n "$owner_mtime" && $((now - owner_mtime)) -ge "$ttl" ]]; then
      rm -rf "$lock_dir" 2>/dev/null || true
      continue
    fi
    if [[ "$attempts" -ge 100 ]]; then
      echo "[state] timed out acquiring lock: $name" >&2
      return 1
    fi
    sleep 0.05
  done
  printf '%s\n' "$$" > "$lock_dir/owner"
  echo "$lock_dir"
}

eneo_release_lock() {
  local lock_dir="${1:-}"
  if [[ -n "$lock_dir" ]]; then
    rm -f "$lock_dir/owner" 2>/dev/null || true
    rmdir "$lock_dir" 2>/dev/null || true
    local lock_root
    lock_root=$(dirname "$lock_dir")
    rmdir "$lock_root" 2>/dev/null || true
  fi
}

# --- Read helpers -------------------------------------------------------------
# Usage: eneo_task_get <jq-expression>
eneo_task_get() {
  local expr="$1"
  local file; file=$(eneo_task_file)
  if [[ ! -f "$file" ]]; then
    echo ""
    return
  fi
  if ! command -v jq >/dev/null 2>&1; then
    echo ""
    return
  fi
  jq -re "$expr" "$file" 2>/dev/null || echo ""
}

# --- Atomic write helper ------------------------------------------------------
# Usage: eneo_task_update <jq-expression> [arg-name arg-value ...]
# Prefix an arg name with "json:" to pass it via --argjson instead of --arg.
# This keeps array/object updates typed without forcing every caller to shell-
# quote JSON into the jq program itself.
_eneo_update_json_file() {
  local file="$1"
  local expr="$2"
  shift 2
  if [[ ! -f "$file" ]]; then
    return 0  # nothing to update
  fi
  if ! command -v jq >/dev/null 2>&1; then
    echo "[state] jq unavailable; cannot update $file" >&2
    return 0
  fi
  local now; now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  local tmp; tmp=$(mktemp)
  # Build jq argv array from the caller's key/value pairs.
  local -a jq_args=(
    --arg __now "$now"
  )
  while (( $# >= 2 )); do
    local key="$1"
    local value="$2"
    if [[ "$key" == json:* ]]; then
      jq_args+=(--argjson "${key#json:}" "$value")
    else
      jq_args+=(--arg "$key" "$value")
    fi
    shift 2
  done
  local full_expr=".last_update = \$__now | ${expr}"
  if ! jq "${jq_args[@]}" "$full_expr" "$file" >"$tmp" 2>/dev/null; then
    rm -f "$tmp"
    echo "[state] jq expression failed: $expr" >&2
    return 1
  fi
  mv "$tmp" "$file"
}

eneo_task_update_unlocked() {
  local file; file=$(eneo_task_file)
  _eneo_update_json_file "$file" "$@"
}

eneo_task_update() {
  local lock_dir
  lock_dir=$(eneo_acquire_lock state) || return 1
  trap 'eneo_release_lock "$lock_dir"' RETURN
  eneo_task_update_unlocked "$@"
}

# --- Phase mirror -------------------------------------------------------------
# Writes the phase string to both .claude/state/phase (fast cat-able single-word
# file) AND to current-task.json.tdd_phase. JSON is authoritative if mirror
# drifts; /eneo-doctor detects the drift and prints a fix.
eneo_phase_set() {
  local phase="$1"
  case "$phase" in
    RED|GREEN|REFACTOR|FREE) ;;
    *)
      echo "[state] invalid phase: $phase (expected RED|GREEN|REFACTOR|FREE)" >&2
      return 2
      ;;
  esac
  eneo_task_update '.tdd_phase = $__phase' __phase "$phase" || true
  local pf; pf=$(eneo_phase_file)
  mkdir -p "$(dirname "$pf")" 2>/dev/null || true
  printf '%s\n' "$phase" > "$pf"
}

eneo_next_hint_consume() {
  local file; file=$(eneo_task_file)
  if [[ ! -f "$file" ]]; then
    echo ""
    return 0
  fi
  if ! command -v jq >/dev/null 2>&1; then
    echo ""
    return 0
  fi

  local lock_dir hint
  lock_dir=$(eneo_acquire_lock state) || return 1
  trap 'eneo_release_lock "$lock_dir"' RETURN
  hint=$(jq -re '.next_hint // empty' "$file" 2>/dev/null || echo "")
  _eneo_update_json_file "$file" '.next_hint = null' || return 1
  printf '%s\n' "$hint"
}

# --- Initial creation (called only by /eneo-new) -----------------------------
# Usage: eneo_task_init <slug> <lane> <bracket> <tenancy_impact> <audit_impact>
eneo_task_init() {
  local slug="$1" lane="$2" bracket="$3" tenancy="$4" audit="$5"
  local file; file=$(eneo_task_file)
  mkdir -p "$(dirname "$file")"
  local now; now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  local tmp; tmp=$(mktemp)
  jq -n \
    --arg slug "$slug" --arg lane "$lane" --argjson bracket "$bracket" \
    --arg tenancy "$tenancy" --arg audit "$audit" --arg now "$now" \
    '{
      slug: $slug,
      lane: $lane,
      bracket: $bracket,
      tenancy_impact: $tenancy,
      audit_impact: $audit,
      phase: null,
      phase_total: null,
      phase_name: null,
      tdd_phase: "FREE",
      wave: null,
      wave_total: null,
      wave_status: {},
      active_agents: [],
      status: "in_progress",
      started_at: $now,
      last_update: $now,
      next_hint: null,
      prd_issue: null,
      last_pr: null
    }' > "$tmp"
  mv "$tmp" "$file"
}

# --- Deletion (called only by /eneo-recap) -----------------------------------
eneo_task_clear() {
  local file; file=$(eneo_task_file)
  rm -f "$file"
  local pf; pf=$(eneo_phase_file)
  printf 'FREE\n' > "$pf" 2>/dev/null || true
}
