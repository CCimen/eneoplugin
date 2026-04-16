#!/usr/bin/env bash
# SessionStart — if the harness plugins are not installed, print install hints.
# Per playbook Decision 0.1 bootstrap flow step 3.
# Always exits 0; this is informational only.

set -euo pipefail

# List plugins (works whether we're on host or in-container because
# Claude Code is the one running us).
if command -v claude >/dev/null 2>&1; then
  INSTALLED=$(claude plugin list 2>/dev/null || true)
  if ! echo "$INSTALLED" | grep -q "eneo-core"; then
    cat >&2 <<'EOF'
[eneo-bootstrap] Run these once to install the agent harness:
  /plugin marketplace add eneo-ai/eneo-agent-harness
  /plugin install eneo-core@eneo-agent-harness
  /plugin install eneo-standards@eneo-agent-harness
  /plugin install eneo-findings@eneo-agent-harness
EOF
  fi
fi

exit 0
