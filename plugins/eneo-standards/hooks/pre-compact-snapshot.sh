#!/usr/bin/env bash
# PreCompact — persist the current phase scratchpad to .claude/context/ so
# wave artifacts survive conversation compaction.
# Wave artifacts live under .claude/phases/<slug>/scratchpad/ (written by
# subagents during /gsd-execute-phase), or in CLAUDE_SCRATCHPAD_DIR if set.

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/env.sh"

ROOT=$(eneo_repo_root)
SLUG=$(eneo_current_slug)
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)

if [[ -z "$SLUG" ]]; then
  exit 0  # nothing to snapshot
fi

# Source: either CLAUDE_SCRATCHPAD_DIR or the phase scratchpad
SRC="${CLAUDE_SCRATCHPAD_DIR:-$ROOT/.claude/phases/$SLUG/scratchpad}"
if [[ ! -d "$SRC" ]]; then
  exit 0
fi

DEST_DIR="$ROOT/.claude/context"
mkdir -p "$DEST_DIR"
DEST="$DEST_DIR/${SLUG}-${TIMESTAMP}.md"

{
  echo "# Scratchpad snapshot — slug: $SLUG, timestamp: $TIMESTAMP"
  echo
  echo "Captured at PreCompact. Source: $SRC"
  echo
  for f in "$SRC"/*; do
    [[ -f "$f" ]] || continue
    echo "## $(basename "$f")"
    echo
    echo '```'
    cat "$f"
    echo '```'
    echo
  done
} > "$DEST"

echo "[pre-compact] snapshotted scratchpad to $DEST" >&2
exit 0
