---
description: Open a PR for the current phase via gh. Enforces tenancy/audit/PRD/phase metadata; Stop-hook validator fails the ship if any field is missing.
argument-hint: "[<phase-number>]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash(gh pr *)
  - Bash(git *)
  - Bash(jq *)
model: sonnet
hooks:
  Stop:
    - hooks:
        - type: command
          command: >-
            bash -c '
              PR=$(jq -r ".last_pr // empty" "$CLAUDE_PROJECT_DIR/.claude/state/current-task.json" 2>/dev/null);
              if [[ -n "$PR" ]]; then
                python3 "${CLAUDE_PLUGIN_ROOT:-$CLAUDE_PROJECT_DIR/plugins/eneo-standards}/hooks/validators/pr_metadata_check.py" --pr "$PR";
              fi
            '
---

# /eneo-ship

Open a PR for the current phase. The Stop-hook validator fails the command if the PR body is missing `tenancy:*`, `audit:*`, `PRD: #<issue>`, `Phase: <N>`, or the `## Verify evidence` section.

## Pre-flight

- Require `current-task.json.status == "verified"`. Otherwise print `Next: /eneo-verify` and exit.
- Confirm branch is ahead of the base and has no uncommitted changes. If uncommitted, print `Fix: stage + commit via git (the harness never bypasses commit hooks).`

## PR body template

Use exactly these sections — the validator is regex-driven:

```markdown
## Summary
<1–3 bullets from .claude/phases/<slug>/phase-<NN>-verify.md>

## Metadata
- **PRD:** #<prd_issue>
- **Phase:** <N>
- **tenancy:** <tenancy_impact>
- **audit:** <audit_impact>
- **lane:** <lane>

## Verify evidence
<verbatim copy of .claude/phases/<slug>/phase-<NN>-verify.md>

## Test plan
- [ ] Reviewer replays the evidence commands
- [ ] Reviewer checks audit-log rows for touched endpoints in staging
- [ ] Reviewer confirms tenancy isolation in staging smoke env
```

Attribution: include a `Co-Authored-By: Claude <noreply>` footer when committing via the Anthropic attribution settings pattern.

## Flow

1. Read `current-task.json` for slug, phase, PRD issue, tenancy/audit tags.
2. `gh pr create --title "<slug> phase <N>: <phase_name>" --body-file <tmp>` (with the template populated). Capture PR number.
3. `eneo_task_update '.last_pr = $__pr | .next_hint = "/eneo-start (phase <M+1>)"'` `__pr "<NNN>"` (where M+1 is the next phase; use `"/eneo-recap"` if this was the last phase).
4. Post a summary comment on the PRD issue referencing the new PR. **Never close** the PRD issue here (Pocock rule: PRD issue closes only in `/eneo-recap`).
5. Stream:
   ```
   ✓ PR #<NNN> opened at <url>
     Linked to PRD issue #<prd_issue>
     Next: /eneo-start <slug> <M+1>   (or /eneo-recap if this was the last phase)
   ```

## Validator behavior

The `pr_metadata_check.py` validator reads the new PR body via `gh pr view <n> --json body` and accepts the markdown label style shown above (`**PRD:**`, `**Phase:**`, `**tenancy:**`, `**audit:**`). If any required pattern is absent it fails with exit 2, Claude re-loops on stderr, and edits the PR body via `gh pr edit`. Do not bypass.
