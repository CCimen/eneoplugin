#!/usr/bin/env bash
# PreToolUse:Edit|Write|MultiEdit — TDD phase gate.
# Blocks test edits during GREEN; blocks src/ edits in intric/ during RED.
# Exit code 2 (exit 1 is silently swallowed — GH issue anthropics/claude-code#21988).
# Fails open on infra errors (missing state file = FREE phase, no block).

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/env.sh"

INPUT=$(cat)
PHASE=$(eneo_phase)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null || echo "")

# Empty file path = pass through; the tool schema handles validation.
if [[ -z "$FILE" ]]; then
  exit 0
fi

is_test=false
case "$FILE" in
  */tests/*|*_test.py|*/test_*.py|*.test.ts|*.test.tsx|*.spec.ts|*.spec.tsx|*/__tests__/*)
    is_test=true
    ;;
esac

is_intric_src=false
case "$FILE" in
  *backend/src/intric/*)
    if [[ "$is_test" == "false" ]]; then
      is_intric_src=true
    fi
    ;;
esac

case "$PHASE" in
  GREEN)
    if [[ "$is_test" == "true" ]]; then
      SLUG=$(eneo_current_slug)
      SLUG=${SLUG:-<slug>}
      {
        echo "✗ Blocked: attempted to edit test file during GREEN phase."
        echo "  Rule: tests are frozen during GREEN to prevent test-gaming under context pressure (.claude/rules/eneo-context.md#tdd)."
        echo "  Fix:  edit src/ to make the failing test pass. If the test itself is genuinely wrong,"
        echo "        run '/eneo-start $SLUG --phase red' to unfreeze. Run '/eneo-doctor' if the state feels stale."
      } >&2
      exit 2
    fi
    ;;
  RED)
    if [[ "$is_intric_src" == "true" ]]; then
      SLUG=$(eneo_current_slug)
      SLUG=${SLUG:-<slug>}
      {
        echo "✗ Blocked: attempted to edit $FILE during RED phase."
        echo "  Rule: RED phase requires a failing test before src/ edits (.claude/rules/eneo-context.md#tdd)."
        echo "  Fix:  add the failing test first. /eneo-start $SLUG advances to GREEN automatically when the wave barrier clears."
        echo "        Escape hatch: '/eneo-start $SLUG --phase green'."
      } >&2
      exit 2
    fi
    ;;
esac

exit 0
