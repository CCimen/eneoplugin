#!/usr/bin/env bash
# Stop — coverage + mutation ratchet gate (Section D Mechanism 4).
# Soft-fails when no ratchet baseline exists yet. Once a task reaches
# current-task.json.status=verified, missing current artifacts become a hard
# failure so shipping cannot silently skip the ratchet.

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/env.sh"

ROOT=$(eneo_repo_root)
COV="$ROOT/.claude/ratchet/coverage.json"
MUT="$ROOT/.claude/ratchet/mutation.json"
CURRENT_DIR="$ROOT/.claude/ratchet/.current"
CURRENT_COV="$CURRENT_DIR/coverage.json"
CURRENT_MUT="$CURRENT_DIR/mutation.json"

# Missing ratchet files = first run; nothing to enforce yet.
if [[ ! -f "$COV" && ! -f "$MUT" ]]; then
  exit 0
fi

TASK_FILE="$ROOT/.claude/state/current-task.json"
TASK_STATUS=$(jq -r '.status // ""' "$TASK_FILE" 2>/dev/null || echo "")

# Compare the committed baselines to current artifacts.
# This wrapper is intentionally pure-Python-safe: ratchet_check.py only reads
# JSON files and does not shell out to uv/pytest/mutmut, so calling python3
# directly does not bypass eneo_exec-sensitive toolchains.
# Before /eneo-verify the hook stays soft on missing current artifacts; after a
# phase is marked verified it blocks ship on missing or regressed artifacts.
VALIDATOR="$(dirname "${BASH_SOURCE[0]}")/validators/ratchet_check.py"
if [[ -f "$VALIDATOR" ]]; then
  VALIDATOR_ARGS=(--coverage "$COV" --mutation "$MUT" --repo-root "$ROOT")
  if [[ -f "$CURRENT_COV" ]]; then
    VALIDATOR_ARGS+=(--current-coverage "$CURRENT_COV")
  fi
  if [[ -f "$CURRENT_MUT" ]]; then
    VALIDATOR_ARGS+=(--current-mutation "$CURRENT_MUT")
  fi
  if [[ "$TASK_STATUS" != "verified" ]]; then
    VALIDATOR_ARGS+=(--allow-missing-current)
  fi
  if ! python3 "$VALIDATOR" "${VALIDATOR_ARGS[@]}"; then
    echo "[stop-ratchet] coverage or mutation regression detected — see above." >&2
    exit 2
  fi
fi

exit 0
