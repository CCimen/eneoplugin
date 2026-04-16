#!/usr/bin/env bash
# UserPromptSubmit — log the prompt, refresh current-task.last_update, and
# surface the current slug/phase to Claude via stderr.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/env.sh
source "$HOOK_DIR/lib/env.sh" 2>/dev/null || true
# shellcheck source=lib/state.sh
source "$HOOK_DIR/lib/state.sh" 2>/dev/null || true

ROOT=$(eneo_repo_root)
SLUG=$(eneo_current_slug)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if [[ -n "$SLUG" ]]; then
  echo "[eneo-audit] current slug: $SLUG (phase=$(eneo_phase))" >&2
fi

# Log the prompt to .claude/stats/prompts.jsonl for /eneo-prune usage metrics.
INPUT=$(cat 2>/dev/null || echo '{}')
PROMPT=$(echo "$INPUT" | jq -r '.user_prompt // .prompt // ""' 2>/dev/null || echo "")
if [[ -n "$PROMPT" ]]; then
  STATS_DIR="$ROOT/.claude/stats"
  if [[ -n "$SLUG" || -d "$STATS_DIR" ]]; then
    mkdir -p "$STATS_DIR" 2>/dev/null || true
    if command -v shasum >/dev/null 2>&1; then
      HASH=$(echo -n "$PROMPT" | shasum -a 256 | cut -c1-16)
    else
      HASH=$(echo -n "$PROMPT" | sha256sum | cut -c1-16)
    fi
    LEN=${#PROMPT}
    echo "{\"ts\":\"$TS\",\"slug\":\"$SLUG\",\"hash\":\"$HASH\",\"len\":$LEN}" \
      >> "$STATS_DIR/prompts.jsonl" 2>/dev/null || true
    if [[ -f "$STATS_DIR/prompts.jsonl" ]]; then
      LINE_COUNT=$(wc -l < "$STATS_DIR/prompts.jsonl" 2>/dev/null | tr -d ' ' || echo 0)
      if [[ "${LINE_COUNT:-0}" -gt 2000 ]]; then
        TMP=$(mktemp)
        tail -n 2000 "$STATS_DIR/prompts.jsonl" > "$TMP" 2>/dev/null || true
        mv "$TMP" "$STATS_DIR/prompts.jsonl" 2>/dev/null || rm -f "$TMP"
      fi
    fi
  fi
fi

# Refresh current-task.json.last_update so the status line reflects activity.
# eneo_task_update is a no-op when the file does not exist.
eneo_task_update '.' || true

exit 0
