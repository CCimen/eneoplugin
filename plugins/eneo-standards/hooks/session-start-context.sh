#!/usr/bin/env bash
# SessionStart — inform Claude about the current task state and loaded rules.
# Soft-fails silently on any missing artifact.

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/env.sh"

ROOT=$(eneo_repo_root)
STATE="$ROOT/.claude/state/current-task.json"
RULES="$ROOT/.claude/rules/eneo-context.md"

if [[ -f "$STATE" ]]; then
  if command -v jq >/dev/null 2>&1; then
    SUMMARY=$(jq -r '[.slug // "", (.phase // ""), (.phase_total // ""), (.wave // ""), (.wave_total // ""), (.tdd_phase // "FREE"), (.next_hint // "")] | @tsv' "$STATE" 2>/dev/null || echo "")
    if [[ -n "$SUMMARY" ]]; then
      IFS=$'\t' read -r SLUG PHASE PHASE_TOTAL WAVE WAVE_TOTAL TDD_PHASE NEXT_HINT <<<"$SUMMARY"
      if [[ -n "$SLUG" ]]; then
        LINE="Resume: $SLUG"
        if [[ -n "$PHASE" && -n "$PHASE_TOTAL" ]]; then
          LINE+=" · Phase $PHASE/$PHASE_TOTAL"
        fi
        if [[ -n "$WAVE" && -n "$WAVE_TOTAL" ]]; then
          LINE+=" · Wave $WAVE/$WAVE_TOTAL"
        fi
        if [[ -n "$TDD_PHASE" && "$TDD_PHASE" != "FREE" ]]; then
          LINE+=" · $TDD_PHASE"
        fi
        if [[ -n "$NEXT_HINT" ]]; then
          LINE+=" · Next: $NEXT_HINT"
        fi
        printf '%s\n' "$LINE"
      fi
    fi
  fi
fi

if [[ -f "$RULES" ]]; then
  LINES=$(wc -l < "$RULES" | tr -d ' ')
  echo "[eneo-context] loaded eneo-context.md ($LINES lines) from $RULES" >&2
fi

PHASE=$(eneo_phase)
if [[ "$PHASE" != "FREE" ]]; then
  echo "[eneo-context] current TDD phase: $PHASE" >&2
fi

exit 0
