---
description: List stale skills (not triggered in 90 days) and recaps older than 6 months for archive decision. Never auto-deletes — always prints a review table and waits for the developer.
argument-hint: "[--archive <name>]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(git log *)
  - Bash(mv *)
  - Bash(find *)
  - Bash(jq *)
model: sonnet
---

# /eneo-prune

Quarterly housekeeping. SuperClaude Reflexion + agent-os active-curation (not just accumulation).

## Usage

- `/eneo-prune` — list stale skills and old recaps with `[keep|archive]` recommendations.
- `/eneo-prune --archive <name>` — move the named skill or recap to `.claude/archive/`.

## Stale-skill detection

Read `.claude/stats/skill-usage.jsonl` (populated by `user-prompt-audit.sh` + SessionStart). For every skill under `plugins/eneo-*/skills/`, compute last-trigger timestamp. Candidates for archive: no trigger in 90 days.

Stream a table:

```
stale skills (no trigger in 90 days):
  plugins/eneo-core/skills/<name>  last=<date>  suggest: archive
  plugins/eneo-core/skills/<name>  last=<date>  suggest: keep (core doc)
```

## Old-recap detection

`.claude/recaps/*.md` older than 6 months:

```
old recaps (> 6 months):
  .claude/recaps/<slug>.md  shipped=<date>  suggest: archive
```

## Decision

Print the candidate list and a one-line instruction:

```
Review the list above. Archive individual items with:
  /eneo-prune --archive <plugins/eneo-core/skills/<name>|.claude/recaps/<slug>.md>
Next: back to your work — no auto-deletion.
```

## Archive handler (when `--archive <path>` is given)

1. Validate path is a skill directory under `plugins/eneo-*/skills/` or a file under `.claude/recaps/`. Reject otherwise.
2. `mv <path> .claude/archive/<timestamp>-<basename>`.
3. Print:
   ```
   ✓ Archived <path> → .claude/archive/<timestamp>-<basename>
     Next: /eneo-prune to continue reviewing, or back to your work
   ```

## DX rules

- Never deletes; only moves to `.claude/archive/`.
- Never uses `AskUserQuestion` — the table IS the decision surface.
- Prints the `Next:` hint always.
