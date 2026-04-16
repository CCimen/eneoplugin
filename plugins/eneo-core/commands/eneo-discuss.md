---
description: Socratic interview + scope lockdown for Deep-lane PRDs. Runs Pocock's interview script with the SuperClaude 90/70 confidence gate. Soft-requires plan mode; dispatches a read-only Explore subagent to verify assertions against the repo.
argument-hint: "[<slug>]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
  - Edit
  - Write
model: opus
---

# /eneo-discuss

Run a structured Socratic interview over a draft PRD and raise or lower confidence until it crosses the 90/70 gate. Deep lane only — Standard and Fast lanes skip this step.

## Pre-flight

1. Read `.claude/state/current-task.json`. If `lane != "deep"`, print:
   ```
   ✗ /eneo-discuss is Deep-lane only. Current lane: <lane>.
     Fix: run /eneo-start to proceed, or /eneo-new to re-classify.
   ```
   and exit.

2. Recommend plan mode. If the developer is not in plan mode, print once:
   ```
   Hint: plan mode keeps the interview exploratory. Press Shift+Tab to enter.
   ```
   Do not block; continue.

3. Determine slug — `$ARGUMENTS` takes precedence, otherwise `current-task.json.slug`. If neither is present, print `Next: /eneo-new "<description>"` and exit.

## Interview script (Pocock, verbatim prompts)

Stream one section at a time; confirm between sections.

1. **Problem statement.** "Describe the problem in detail. Who feels the pain; how do you know it's happening; what would success look like." Verify the PRD's Problem statement against the answer. If they diverge, edit the PRD.
2. **Repo assertions.** Dispatch a read-only Explore subagent (fresh context) with the PRD's `Module sketch`, `Success criteria`, and `Acceptance criteria`. Instruct it to return `CONFIRMED|<file:line>` or `CONTRADICTED|<file:line> — <reason>` for each claim. Print each return in real time.
3. **Alternatives.** "Which options did you consider? Why reject each?" Record.
4. **Scope.** "Hammer out the exact scope. What is explicitly **out** of scope?" Update `## Out of scope` in the PRD accordingly.

## Confidence gate (SuperClaude 90/70)

Compute a confidence score 0–100 based on:

- Problem statement has a named actor + measurable pain signal (+20)
- Success criteria are numeric or command-executable (Section B BAD/GOOD rule) (+20)
- Every `CONTRADICTED` from the Explore subagent has been reconciled in the PRD (+20)
- Out of scope is populated (+10)
- Open questions labeled (not silently dropped) (+10)
- At least one security/authz user story when auth surface touched (+10)
- Swedish-language UX / a11y story when frontend touched (+10)

Then:

- **≥ 90%** — print `✓ Confidence <N>% — ready to plan. Next: /eneo-plan` and exit.
- **70–89%** — present 2–3 concrete alternatives / clarifying questions and ask the developer to answer. Re-score; loop.
- **< 70%** — block with specific missing items. Print `Confidence <N>% — not ready. Fill the gaps above and re-run.` Exit 0; do not proceed.

## DX rules

- Stream each interview section and each Explore `CONFIRMED|CONTRADICTED` return as it happens; never batch.
- Use `AskUserQuestion` only between the interview sections when the developer needs to choose between alternatives. Do not prompt for anything else.
- The final line is always `Next: <command>` inferred from the gate result.
