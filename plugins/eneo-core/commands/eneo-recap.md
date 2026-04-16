---
description: Close the milestone. Only runs when all phases are shipped. Writes an agent-os-style milestone recap, closes the PRD issue with a recap link, archives the phases dir, and dispatches the learning-extractor subagent for skill candidates.
argument-hint: "[<slug>]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
  - Bash(gh issue *)
  - Bash(git *)
  - Bash(mv *)
  - Bash(jq *)
model: sonnet
---

# /eneo-recap

Finalize a Deep-lane milestone. Pre-flight checks prevent premature closure.

## Pre-flight

- Determine slug (arg or `current-task.json.slug`).
- Confirm every phase file under `.claude/phases/<slug>/` has frontmatter `status: shipped`. List any missing and print:
  ```
  ✗ Cannot recap — phase <N> is not shipped yet.
    Fix: run /eneo-start <slug> <N> → /eneo-verify → /eneo-ship first.
    Next: /eneo-start <slug>
  ```
  and exit.
- Confirm PRD issue number from `current-task.json.prd_issue`.

## Generate recap

Write `.claude/recaps/<slug>.md` following the agent-os recap convention (short, context-focused, not a changelog). This is a milestone artifact, distinct from Claude Code's built-in `/recap` session summary:

```markdown
# Recap: <slug>

**Shipped:** <YYYY-MM-DD>
**PRD:** #<prd_issue>
**Lane:** deep
**Phases:** <N>

## Why we built this
<2 sentences from PRD problem statement>

## What changed
- <bullet per phase>

## Tests and gates
- pyright strict ✓
- pytest ✓
- mutation score <range>%
- audit-log completeness ✓
- tenancy isolation ✓
- adversarial review: <outcome or "skipped (low-risk")>

## Surprises worth remembering
<free-form; extracted from the context snapshots and scratchpads>

## Related
- PRs: <links>
- PRD issue: #<prd_issue>
```

## Archive

```bash
mv .claude/phases/<slug> .claude/archive/
```

Do NOT move `.claude/prds/<slug>.md` or `.claude/plans/<slug>.md` — those stay as historical record under their original paths.

## Close PRD issue

```bash
gh issue close <prd_issue> --comment "Recap: see .claude/recaps/<slug>.md"
```

## Learning extraction

Dispatch the `learning-extractor` subagent (fresh context) with the recap + scratchpad directory. If it proposes skill candidates, stream:

```
✓ learning-extractor proposes <N> skill candidate(s):
  - <name> — <short description>
Next: /finding-teach <name>   (one at a time; eval files required)
```

If no candidates → print nothing for that section.

## Clear state

Call `eneo_task_clear` from `lib/state.sh` to remove `.claude/state/current-task.json` and reset the phase mirror to `FREE`.

## Final output

```
✓ Milestone <slug> closed.
  Recap: .claude/recaps/<slug>.md
  PRD issue #<prd_issue> closed.
  Next: /eneo-new "<next description>"
```
