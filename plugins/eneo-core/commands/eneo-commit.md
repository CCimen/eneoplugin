---
description: Review the staged commit before it lands. Runs deterministic preflight + commit-message checks, invokes security-reviewer only on risky diffs, then commits through normal git hooks.
argument-hint: "<commit-message>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
  - Bash(git *)
  - Bash(jq *)
  - Bash(eneo-commit-preflight *)
  - Bash(eneo-commit-message-check *)
  - Bash(eneo-task-update *)
model: sonnet
---

# /eneo-commit

Create a commit without skipping the repo's normal git hooks. Keep this step terse and deterministic: helper output first, then optional risk review, then the actual `git commit`.

## Pre-flight

- If `$ARGUMENTS` is empty, ask one concise question for the commit message and wait.
- Require staged changes. The source of truth is `eneo-commit-preflight --json`; do not re-implement its checks manually.
- Run:
  - `eneo-commit-preflight --json`
  - `eneo-commit-message-check --json --message "$ARGUMENTS"`
- If either helper returns hard failures:
  - print a short `✗ Commit blocked` section
  - include each concrete failure as a bullet
  - do **not** call `git commit`
  - end with one `Fix:` line and stop

## Advisory signals

The preflight helper may return warnings and signals:

- branch naming needs attention
- staged route files likely need OpenAPI review
- staged behavior changes likely deserve a minimal docs or docs-site follow-up
- risky paths justify a `security-reviewer` pass

Warnings alone are not a block. Surface them concisely; do not turn them into a wall of text.

## Conditional security review

Only if `security_review_needed == true` from the preflight JSON:

1. Spawn the `security-reviewer` subagent with the staged file list as scope.
2. Tell it to inspect only the staged diff / affected files, not the whole repo.
3. If it returns `PASS`, continue silently.
4. If it returns concrete file:line bullets:
   - print them under `Security review`
   - ask one concise question:
     `Commit anyway, or fix the concerns first?`
   - default recommendation: fix first

Do **not** block solely on the subagent's opinion. Deterministic helper failures block; security-reviewer findings escalate to the developer for a final choice.

## Commit

If there are no hard failures and no unresolved security escalation:

1. Run `git commit -m "$ARGUMENTS"`.
2. Let `git commit` run the repository's normal commit hooks. Never bypass them.
3. If `git commit` fails, stream the real stderr / hook output and stop.
4. If `.claude/state/current-task.json` exists, update `next_hint` to `/eneo-ship` via:
   - `eneo-task-update '.next_hint = "/eneo-ship"'`

## Output

On success:

```text
✓ Commit created on <branch>
  Message: <subject>
  Next: /eneo-ship
```

If warnings existed, add a short `Notes:` block after the success message:

- branch naming note, if any
- `OpenAPI follow-up likely`
- `Docs follow-up likely`

Do not auto-edit docs in this command. Suggest the follow-up surgically; let the developer decide whether to bundle it into the same branch.
