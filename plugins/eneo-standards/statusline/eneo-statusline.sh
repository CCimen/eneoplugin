#!/usr/bin/env bash
# Eneo harness custom status line — Claude Code-compatible.
# Reads Claude Code's JSON input on stdin AND .claude/state/current-task.json
# for harness state. Prints two lines; line 2 is omitted when no milestone is
# in flight.
#
# Enable by adding this to .claude/settings.json:
#   "statusLine": {
#     "type": "command",
#     "command": "${CLAUDE_PLUGIN_ROOT}/statusline/eneo-statusline.sh"
#   }
#
# Test without Claude Code:
#   echo '{"model":{"display_name":"Opus 4.7"},"workspace":{"current_dir":"/eneo"},"context_window":{"used_percentage":42},"cost":{"total_cost_usd":0.18,"total_duration_ms":720000},"session_id":"test"}' \
#     | ./eneo-statusline.sh

set -uo pipefail  # no -e: defensive fallback is the whole point

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Source env library for detect_env / eneo_current_slug / phase / repo root.
# Fail silently if missing — the status line should still render line 1.
if [[ -f "$SCRIPT_DIR/../hooks/lib/env.sh" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/../hooks/lib/env.sh" 2>/dev/null || true
fi

# --- ANSI colors -------------------------------------------------------------
C_RESET=$'\033[0m'
C_DIM=$'\033[2m'
C_BOLD=$'\033[1m'
C_RED=$'\033[31m'
C_GREEN=$'\033[32m'
C_YELLOW=$'\033[33m'
C_CYAN=$'\033[36m'

# --- Parse Claude Code stdin -------------------------------------------------
INPUT="$(cat 2>/dev/null || echo '{}')"

_jq() {
  # Safe jq: returns empty string on any parse error
  echo "$INPUT" | jq -r "$1 // \"\"" 2>/dev/null || echo ""
}

MODEL="$(_jq '.model.display_name')"
[[ -z "$MODEL" ]] && MODEL="Claude"
SESSION_NAME="$(_jq '.session_name')"
CWD="$(_jq '.workspace.current_dir')"
[[ -z "$CWD" ]] && CWD="$(pwd)"
WORKTREE_NAME="$(_jq '.workspace.git_worktree')"
CTX_PCT="$(_jq '.context_window.used_percentage')"
COST_USD="$(_jq '.cost.total_cost_usd')"
DURATION_MS="$(_jq '.cost.total_duration_ms')"
RATE_5H="$(_jq '.rate_limits.five_hour.used_percentage')"
RATE_7D="$(_jq '.rate_limits.seven_day.used_percentage')"
SESSION_ID="$(_jq '.session_id')"

# --- Cache git branch per session to avoid repeated calls --------------------
GIT_CACHE_DIR="${TMPDIR:-/tmp}/eneo-statusline-cache"
mkdir -p "$GIT_CACHE_DIR" 2>/dev/null || true
GIT_CACHE_FILE="$GIT_CACHE_DIR/${SESSION_ID:-nosession}.branch"
BRANCH=""

file_mtime() {
  if stat -f %m "$1" >/dev/null 2>&1; then
    stat -f %m "$1"
  else
    stat -c %Y "$1"
  fi
}

if [[ -n "$SESSION_ID" && -f "$GIT_CACHE_FILE" ]]; then
  NOW_TS=$(date +%s)
  CACHE_TS=$(file_mtime "$GIT_CACHE_FILE" 2>/dev/null || echo 0)
  if [[ -n "$CACHE_TS" && $((NOW_TS - CACHE_TS)) -lt 5 ]]; then
    IFS='|' read -r BRANCH STAGED_COUNT MODIFIED_COUNT < "$GIT_CACHE_FILE"
  fi
fi
if [[ -z "$BRANCH" ]]; then
  if git -C "$CWD" rev-parse --git-dir >/dev/null 2>&1; then
    BRANCH="$(git -C "$CWD" branch --show-current 2>/dev/null || echo "")"
    STAGED_COUNT="$(git -C "$CWD" diff --cached --numstat 2>/dev/null | wc -l | tr -d ' ')"
    MODIFIED_COUNT="$(git -C "$CWD" diff --numstat 2>/dev/null | wc -l | tr -d ' ')"
  else
    STAGED_COUNT=0
    MODIFIED_COUNT=0
  fi
  if [[ -n "$SESSION_ID" ]]; then
    printf '%s|%s|%s\n' "$BRANCH" "${STAGED_COUNT:-0}" "${MODIFIED_COUNT:-0}" > "$GIT_CACHE_FILE"
  fi
fi

# --- Format helpers ----------------------------------------------------------
fmt_duration_ms() {
  local ms="$1"
  [[ -z "$ms" || "$ms" == "null" ]] && { echo ""; return; }
  local s=$((ms / 1000))
  if   (( s < 60   )); then printf '%ds'  "$s"
  elif (( s < 3600 )); then printf '%dm'  $((s / 60))
  else                      printf '%dh%dm' $((s / 3600)) $(((s % 3600) / 60))
  fi
}

fmt_cost() {
  local cost="$1"
  [[ -z "$cost" || "$cost" == "null" ]] && { echo ""; return; }
  printf '$%.2f' "$cost"
}

fmt_rate_limit() {
  local label="$1"
  local pct="$2"
  [[ -z "$pct" || "$pct" == "null" ]] && { echo ""; return; }
  local rounded
  rounded=$(printf '%.0f' "$pct")
  if (( rounded >= 70 )); then
    printf '%s%s %s%%%s' "$C_YELLOW" "$label" "$rounded" "$C_RESET"
  else
    echo ""
  fi
}

context_color() {
  local pct="$1"
  [[ -z "$pct" ]] && { echo "$C_DIM"; return; }
  if   (( $(printf '%.0f' "$pct") >= 90 )); then echo "$C_RED"
  elif (( $(printf '%.0f' "$pct") >= 70 )); then echo "$C_YELLOW"
  else                                           echo "$C_GREEN"
  fi
}

dir_name() {
  basename "${1:-.}"
}

# --- Devcontainer awareness --------------------------------------------------
DOCKER_BADGE=""
if declare -f detect_env >/dev/null 2>&1; then
  MODE=$(detect_env 2>/dev/null || echo "native")
  case "$MODE" in
    host-with-docker)
      CONTAINER=""
      if declare -f eneo_container_name >/dev/null 2>&1; then
        CONTAINER=$(eneo_container_name 2>/dev/null || echo "")
      fi
      if [[ -n "$CONTAINER" ]]; then
        DOCKER_BADGE=" ${C_CYAN}◈${C_RESET}"
      else
        DOCKER_BADGE=" ${C_RED}◈!${C_RESET}"
      fi
      ;;
  esac
fi

# --- Line 1 ------------------------------------------------------------------
CTX_DISPLAY=""
if [[ -n "$CTX_PCT" ]]; then
  CTX_COLOR=$(context_color "$CTX_PCT")
  CTX_DISPLAY="${CTX_COLOR}${CTX_PCT}% ctx${C_RESET}"
fi

COST_DISPLAY=$(fmt_cost "$COST_USD")
DURATION_DISPLAY=$(fmt_duration_ms "$DURATION_MS")
DIR_DISPLAY=$(dir_name "$CWD")
RATE_5H_DISPLAY=$(fmt_rate_limit "5h" "$RATE_5H")
RATE_7D_DISPLAY=$(fmt_rate_limit "7d" "$RATE_7D")

MODEL_LABEL="$MODEL"
[[ -n "$SESSION_NAME" ]] && MODEL_LABEL+=" · ${SESSION_NAME}"

LINE1="${C_BOLD}[${MODEL_LABEL}]${C_RESET}${DOCKER_BADGE} ${DIR_DISPLAY}"
[[ -n "$WORKTREE_NAME"   ]] && LINE1+=" · ${C_DIM}wt${C_RESET} ${WORKTREE_NAME}"
[[ -n "$BRANCH"          ]] && LINE1+=" · ${C_CYAN}⎇${C_RESET} ${BRANCH}"
if [[ -n "${STAGED_COUNT:-}" && "${STAGED_COUNT:-0}" != "0" ]]; then
  LINE1+=" · ${C_GREEN}+${STAGED_COUNT}${C_RESET}"
fi
if [[ -n "${MODIFIED_COUNT:-}" && "${MODIFIED_COUNT:-0}" != "0" ]]; then
  LINE1+=" · ${C_YELLOW}~${MODIFIED_COUNT}${C_RESET}"
fi
[[ -n "$CTX_DISPLAY"     ]] && LINE1+=" · ${CTX_DISPLAY}"
[[ -n "$RATE_5H_DISPLAY" ]] && LINE1+=" · ${RATE_5H_DISPLAY}"
[[ -n "$RATE_7D_DISPLAY" ]] && LINE1+=" · ${RATE_7D_DISPLAY}"
[[ -n "$DURATION_DISPLAY" ]] && LINE1+=" · ${DURATION_DISPLAY}"
if [[ "${ENEO_STATUSLINE_SHOW_COST:-0}" == "1" && -n "$COST_DISPLAY" ]]; then
  LINE1+=" · ${COST_DISPLAY}"
fi

printf '%s\n' "$LINE1"

# --- Line 2 — harness state (optional) --------------------------------------
# Find current-task.json via the env helper if available, otherwise best-effort.
STATE_FILE=""
if declare -f eneo_repo_root >/dev/null 2>&1; then
  ROOT=$(eneo_repo_root 2>/dev/null || echo "")
  [[ -n "$ROOT" ]] && STATE_FILE="$ROOT/.claude/state/current-task.json"
else
  STATE_FILE="$CWD/.claude/state/current-task.json"
fi

if [[ -z "$STATE_FILE" || ! -f "$STATE_FILE" ]]; then
  exit 0  # no milestone in flight → line 2 hidden
fi

# Parse state defensively with a single jq call.
STATE_FIELDS="$(jq -r '
  [
    .slug // "",
    (.phase // ""),
    (.phase_total // ""),
    (.wave // ""),
    (.wave_total // ""),
    .tdd_phase // "",
    .status // "",
    .next_hint // "",
    (
      if ((.active_agents // []) | type) == "array"
      then (.active_agents // [])
      else []
      end
    ) | join(", "),
    (.wave_status // {}) | tojson
  ] | @tsv
' "$STATE_FILE" 2>/dev/null || echo "")"

IFS=$'\t' read -r SLUG PHASE PHASE_TOTAL WAVE WAVE_TOTAL TDD_PHASE STATUS NEXT_HINT ACTIVE_AGENTS WAVE_STATUS_JSON <<<"$STATE_FIELDS"
if [[ -z "$SLUG" ]]; then
  exit 0  # malformed or empty → fall back to line 1
fi

# Wave-completion bar
bar() {
  local total="$1"
  # Build per-wave block from wave_status object
  local blocks=""
  if [[ -n "$total" ]]; then
    for ((i=1; i<=total; i++)); do
      local s
      s="$(echo "${WAVE_STATUS_JSON:-{}}" | jq -r --arg key "$i" '.[$key] // "pending"' 2>/dev/null || echo "pending")"
      case "$s" in
        done)        blocks+="▓" ;;
        in_progress) blocks+="▒" ;;
        *)           blocks+="░" ;;
      esac
    done
  fi
  echo "$blocks"
}

# Color the TDD phase
tdd_color() {
  case "$1" in
    RED)      echo "${C_RED}${1}${C_RESET}" ;;
    GREEN)    echo "${C_GREEN}${1}${C_RESET}" ;;
    REFACTOR) echo "${C_YELLOW}${1}${C_RESET}" ;;
    *)        echo "$1" ;;
  esac
}

LINE2="${C_BOLD}${SLUG}${C_RESET}"
if [[ -n "$PHASE" && -n "$PHASE_TOTAL" ]]; then
  LINE2+=" · ${C_DIM}p${C_RESET}${PHASE}/${PHASE_TOTAL}"
fi
if [[ -n "$WAVE" && -n "$WAVE_TOTAL" ]]; then
  BAR=$(bar "$WAVE_TOTAL")
  LINE2+=" · ${C_DIM}w${C_RESET}${WAVE}/${WAVE_TOTAL} [${BAR}]"
fi
if [[ -n "$TDD_PHASE" && "$TDD_PHASE" != "FREE" ]]; then
  LINE2+=" · $(tdd_color "$TDD_PHASE")"
fi
if [[ -n "$ACTIVE_AGENTS" ]]; then
  LINE2+=" · ${C_CYAN}↻${C_RESET} ${ACTIVE_AGENTS}"
elif [[ -n "$NEXT_HINT" ]]; then
  LINE2+=" · ${C_DIM}→${C_RESET} ${NEXT_HINT}"
elif [[ "$STATUS" == "in_progress" ]]; then
  LINE2+=" · ${C_DIM}…${C_RESET}"
fi

printf '%s\n' "$LINE2"
