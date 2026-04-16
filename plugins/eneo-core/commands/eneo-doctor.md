---
description: Run environment diagnostics at any time. Prints the exact command to fix every issue it detects. First thing a new developer runs; first thing anyone runs when something feels off.
argument-hint: ""
allowed-tools:
  - Read
  - Glob
  - Bash(eneo-doctor-report *)
model: sonnet
---

Run `eneo-doctor-report` first and use its output as the canonical diagnostic table. Do not replace it with ad hoc shell probing unless the helper itself fails.

Execution rules:
- Print the helper's `STATUS | CHECK | FIX` table as-is.
- Count failing rows (`✗`) and summarize them at the end.
- Keep your own narration minimal. Do not preface the helper with exploratory prose like "Running diagnostics now." The table itself is the diagnostic output.
- If there are no failing rows, end with:
  - `✓ All checks pass.`
  - `Next: /eneo-new "<description of the change>"` when no active task state exists
  - otherwise infer the next command from the current task state
- If there are failing rows, end with:
  - `✗ <N> check(s) failed. Apply the fixes above, then re-run /eneo-doctor.`
- Never prompt via `AskUserQuestion`.
- Never run exploratory Bash probes after the helper succeeds; the point of this command is deterministic output, not improvisation.
