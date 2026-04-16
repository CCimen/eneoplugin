#!/usr/bin/env bash
# Eneo devcontainer post-create — seed Claude Code and the harness marketplace
# so the container is ready to use the moment it's built.
# Developers still need to provide their own API key on first `claude` run.
#
# Append the body below to your existing .devcontainer/post-create.sh (or
# copy verbatim if you don't have one yet).

set -euo pipefail

# Install Claude Code CLI (harmless if already present)
if ! command -v claude >/dev/null 2>&1; then
  npm install -g @anthropic-ai/claude-code
fi

# Pre-seed the harness marketplace for developers
mkdir -p ~/.claude
if [[ ! -f ~/.claude/settings.json ]]; then
  cat > ~/.claude/settings.json <<'EOF'
{
  "extraKnownMarketplaces": {
    "eneo-agent-harness": {
      "type": "github",
      "repo": "eneo-ai/eneo-agent-harness"
    }
  }
}
EOF
fi

# Nudge developers toward /eneo-doctor first thing
cat <<'EOF'

[eneo-bootstrap] Devcontainer ready. First steps inside Claude Code:
  /plugin install eneo-core@eneo-agent-harness
  /plugin install eneo-standards@eneo-agent-harness
  /plugin install eneo-findings@eneo-agent-harness
  /eneo-doctor

See .claude/bootstrap.md in the Eneo repo for the full flow.
EOF
