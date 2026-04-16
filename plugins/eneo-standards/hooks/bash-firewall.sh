#!/usr/bin/env bash
# PreToolUse:Bash — blocks bash-based bypass of the phase-gate.
# GH issue anthropics/claude-code#29709: PreToolUse hooks only cover Edit/Write,
# file modifications via Bash (python, sed, echo, tee, >) are not intercepted.
# This hook greps destructive patterns against test paths during GREEN.

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/env.sh"

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")
PHASE=$(eneo_phase)

if [[ -z "$CMD" ]]; then
  exit 0
fi

# Always-block shell writes into protected harness files.
if echo "$CMD" | grep -qE '(sed[[:space:]]+-i|tee|>>?|cat[[:space:]]*>)[^|]*\.claude/state/phase'; then
  {
    echo "✗ Blocked: bash modification of .claude/state/phase."
    echo "  Rule: the phase mirror must only be updated through eneo_phase_set so JSON state stays authoritative."
    echo "  Fix:  source hooks/lib/state.sh and call 'eneo_phase_set RED|GREEN|REFACTOR|FREE' instead of redirecting into the file."
  } >&2
  exit 2
fi

if echo "$CMD" | grep -qE '(sed[[:space:]]+-i|tee|>>?|cat[[:space:]]*>)[^|]*(/|^|[[:space:]])(\.env($|\.)|.*\.env(\.[^[:space:]]+)?($|[[:space:]])|bun\.lockb|bun\.lock|uv\.lock|package-lock\.json|pnpm-lock\.yaml|Cargo\.lock|poetry\.lock|\.claude/ratchet/[^[:space:]]+\.json)'; then
  {
    echo "✗ Blocked: bash write into a protected file."
    echo "  Rule: .env files, lockfiles, and ratchet baselines are owned by the developer, package manager, or commit hooks — not ad hoc bash redirects."
    echo "  Fix:  update .env.example for secrets, run the package manager for lockfiles, and let ratchet files be written by their owning workflow."
  } >&2
  exit 2
fi

# Always-block destructive commands regardless of phase
# (catches rm -rf on test dirs even in FREE phase).
if echo "$CMD" | grep -qE 'rm[[:space:]]+-rf?[[:space:]]+.*(tests?/|__tests__/)'; then
  {
    echo "✗ Blocked: bulk deletion of test files via bash."
    echo "  Rule: agents must not remove tests to bypass the phase-gate (.claude/rules/eneo-context.md#protected-paths)."
    echo "  Fix:  if a test is obsolete, delete it through the Edit tool on a per-file basis during REFACTOR phase."
  } >&2
  exit 2
fi

# Phase-scoped: during GREEN, block redirect/sed into test files
if [[ "$PHASE" == "GREEN" ]]; then
  if echo "$CMD" | grep -qE '(sed[[:space:]]+-i|tee|>[[:space:]]*)[^|]*(tests/|_test\.py|\.test\.ts|\.test\.tsx|\.spec\.ts|\.spec\.tsx|__tests__/)'; then
    SLUG=$(eneo_current_slug)
    SLUG=${SLUG:-<slug>}
    {
      echo "✗ Blocked: bash modification of a test file during GREEN."
      echo "  Rule: Edit hooks are bypassed by bash redirects; the firewall enforces the same rule through bash (GH issue anthropics/claude-code#29709)."
      echo "  Fix:  if the test is genuinely wrong, run '/eneo-start $SLUG --phase red' to unfreeze, then edit through the Edit tool."
    } >&2
    exit 2
  fi
fi

# Phase-scoped: during RED, block intric/ src writes via bash
if [[ "$PHASE" == "RED" ]]; then
  if echo "$CMD" | grep -qE '(sed[[:space:]]+-i|tee|>[[:space:]]*)[^|]*backend/src/intric/[^[:space:]]+\.py'; then
    SLUG=$(eneo_current_slug)
    SLUG=${SLUG:-<slug>}
    {
      echo "✗ Blocked: bash modification of backend/src/intric/ during RED."
      echo "  Rule: src edits require a failing test first (.claude/rules/eneo-context.md#tdd)."
      echo "  Fix:  complete the failing test; /eneo-start $SLUG flips to GREEN automatically when the wave barrier clears."
    } >&2
    exit 2
  fi
fi

exit 0
