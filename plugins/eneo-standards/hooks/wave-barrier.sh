#!/usr/bin/env bash
# SubagentStop — wave-completion barrier.
#
# Per Claude Code hook docs, SubagentStop includes `agent_id`, `agent_type`,
# `stop_hook_active`, and `last_assistant_message`. The harness treats
# `DONE|<path>` as a counted completion and `BLOCKED|<reason>` as a finished
# but non-counting return. Duplicate stop events for the same agent_id are
# ignored so re-dispatches cannot double-count.
#
# Two pieces of state:
# 1. .claude/state/wave.json           — authoritative counter
# 2. .claude/state/current-task.json   — DX source of truth
#
# Soft-fails on everything; never blocks.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/env.sh
source "$HOOK_DIR/lib/env.sh" 2>/dev/null || true
# shellcheck source=lib/state.sh
source "$HOOK_DIR/lib/state.sh" 2>/dev/null || true

WAVE=$(eneo_wave_file)

INPUT=$(cat 2>/dev/null || echo '{}')

if [[ ! -f "$WAVE" ]]; then
  exit 0  # no wave in progress
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "[wave-barrier] jq not installed; skipping" >&2
  exit 0
fi

STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null || echo "false")
AGENT_ID=$(echo "$INPUT" | jq -r '.agent_id // ""' 2>/dev/null || echo "")
AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // ""' 2>/dev/null || echo "")
LAST_MESSAGE=$(echo "$INPUT" | jq -r '.last_assistant_message // ""' 2>/dev/null || echo "")

if [[ "$STOP_ACTIVE" == "true" ]]; then
  exit 0
fi

RESULT=""
ARTIFACT=""
case "$LAST_MESSAGE" in
  DONE\|*)
    RESULT="done"
    ARTIFACT="${LAST_MESSAGE#DONE|}"
    ;;
  BLOCKED\|*)
    RESULT="blocked"
    ;;
  *)
    exit 0
    ;;
esac

LOCK_DIR=$(eneo_acquire_lock state) || exit 0
trap 'eneo_release_lock "$LOCK_DIR"' EXIT

# ---- 1. Advance wave.json (authoritative counter) ---------------------------
CURRENT=$(cat "$WAVE" 2>/dev/null || echo '{}')
WAVE_NO=$(echo "$CURRENT" | jq -r '.wave // 1')

if [[ -n "$AGENT_ID" ]] && echo "$CURRENT" | jq -e --arg agent "$AGENT_ID" '.seen_agents // [] | index($agent) != null' >/dev/null 2>&1; then
  echo "[wave-barrier] duplicate SubagentStop for $AGENT_ID ignored" >&2
  exit 0
fi

DONE=$(echo "$CURRENT" | jq '.done // 0')
EXPECTED=$(echo "$CURRENT" | jq '.expected // 0')

if [[ "$RESULT" == "done" ]]; then
  NEW_DONE=$((DONE + 1))
  if [[ "$EXPECTED" -gt 0 && "$NEW_DONE" -ge "$EXPECTED" ]]; then
    STATUS="ready-for-next-wave"
  else
    STATUS="in-progress"
  fi

  TMP=$(mktemp)
  echo "$CURRENT" | jq \
    --argjson d "$NEW_DONE" \
    --arg s "$STATUS" \
    --arg agent "$AGENT_ID" \
    --arg artifact "$ARTIFACT" \
    '.done = $d
     | .status = $s
     | .seen_agents = ((.seen_agents // []) + (if $agent == "" then [] else [$agent] end))
     | .completed_artifacts = ((.completed_artifacts // []) + (if $artifact == "" then [] else [$artifact] end))' > "$TMP"
  mv "$TMP" "$WAVE"

  echo "[wave-barrier] wave $WAVE_NO: $NEW_DONE/$EXPECTED ($STATUS)" >&2

  if [[ "$STATUS" == "ready-for-next-wave" ]]; then
    eneo_task_update_unlocked \
      '.wave_status = ((.wave_status // {}) | .[($__wave|tostring)] = "done") | .active_agents = []' \
      __wave "$WAVE_NO" || true
  else
    eneo_task_update_unlocked \
      '.wave_status = ((.wave_status // {}) | .[($__wave|tostring)] = "in_progress")
       | .active_agents = (
           if ((.active_agents // []) | type) == "array"
           then
             (.active_agents // []) as $agents
             | ($agents | index($__agent_type)) as $idx
             | if $idx == null then $agents else ($agents[0:$idx] + $agents[$idx + 1:]) end
           else []
           end
         )' \
      __wave "$WAVE_NO" \
      __agent_type "$AGENT_TYPE" || true
  fi
else
  TMP=$(mktemp)
  echo "$CURRENT" | jq \
    --arg agent "$AGENT_ID" \
    '.status = "in-progress"
     | .seen_agents = ((.seen_agents // []) + (if $agent == "" then [] else [$agent] end))
     | .blocked_agents = ((.blocked_agents // []) + (if $agent == "" then [] else [$agent] end))' > "$TMP"
  mv "$TMP" "$WAVE"

  echo "[wave-barrier] wave $WAVE_NO: blocked result from ${AGENT_TYPE:-unknown}; not advancing" >&2

  eneo_task_update_unlocked \
    '.wave_status = ((.wave_status // {}) | .[($__wave|tostring)] = "in_progress")
     | .active_agents = (
         if ((.active_agents // []) | type) == "array"
         then
           (.active_agents // []) as $agents
           | ($agents | index($__agent_type)) as $idx
           | if $idx == null then $agents else ($agents[0:$idx] + $agents[$idx + 1:]) end
         else []
         end
       )' \
    __wave "$WAVE_NO" \
    __agent_type "$AGENT_TYPE" || true
fi

exit 0
