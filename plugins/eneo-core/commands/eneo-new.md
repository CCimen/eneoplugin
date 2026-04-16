---
description: Triage + entry point for Fast/Standard/Deep lanes. Classifies the change, writes .claude/state/current-task.json, and creates the right artifact (prompt / SPEC.md / PRD + GitHub issue) based on lane. Prompts only when classification is genuinely borderline.
argument-hint: "<description of the change>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - Bash(git *)
  - Bash(gh issue create *)
  - Bash(date *)
model: sonnet
hooks:
  Stop:
    - hooks:
        - type: command
          command: >-
            bash -c '
              SLUG=$(jq -r ".slug // empty" "$CLAUDE_PROJECT_DIR/.claude/state/current-task.json" 2>/dev/null);
              LANE=$(jq -r ".lane // empty" "$CLAUDE_PROJECT_DIR/.claude/state/current-task.json" 2>/dev/null);
              if [[ "$LANE" = "standard" && -f "$CLAUDE_PROJECT_DIR/.claude/specs/$SLUG/SPEC.md" ]]; then
                python3 "${CLAUDE_PLUGIN_ROOT:-$CLAUDE_PROJECT_DIR/plugins/eneo-standards}/hooks/validators/validate_file_contains.py" \
                  --file ".claude/specs/$SLUG/SPEC.md" \
                  --contains "## Goal" --contains "## Out of scope" --max-lines 100;
              elif [[ "$LANE" = "deep" && -f "$CLAUDE_PROJECT_DIR/.claude/prds/$SLUG.md" ]]; then
                python3 "${CLAUDE_PLUGIN_ROOT:-$CLAUDE_PROJECT_DIR/plugins/eneo-standards}/hooks/validators/validate_file_contains.py" \
                  --file ".claude/prds/$SLUG.md" \
                  --contains "## Problem statement" \
                  --contains "## Success criteria" \
                  --contains "## User stories" \
                  --contains "## Acceptance criteria" \
                  --contains "## Module sketch" \
                  --contains "## Testing decisions" \
                  --contains "## Out of scope" \
                  --contains "## Polishing requirements" \
                  --contains "## Open questions";
              fi
            '
---

# /eneo-new

Triage the developer's request (`$ARGUMENTS`) and create the appropriate artifact for the detected lane. Apply the lane table from the playbook Section A:

| Bracket | Lane | Surface |
|---|---|---|
| 1 | Fast | ≤50 LOC, 1 file, no new dep, no migration, no auth/ACL touch |
| 2 | Fast | ≤200 LOC, ≤3 files, single bounded context in `intric/` |
| 3 | Standard | 200–800 LOC, multi-file, new API surface / SvelteKit route / Pydantic model |
| 4 | Deep | >800 LOC, cross-service, Alembic migration, auth/tenancy, audit-log schema change |

**Bracket-bump rule:** any change touching `audit_log`, `tenant_id` filters, or auth middleware is force-promoted to Deep lane regardless of LOC.

## Steps

### 1. Classify

Read `$ARGUMENTS`. Infer LOC range, files touched, and impact fields.

Before writing any state or printing any success banner, do this decision gate:

1. Is the target specific enough to execute right now?
2. If not, have you already inspected the obvious candidate files for the named artifact?
3. If it is still ambiguous after that inspection, stop and ask one tight clarification question.

Write `.claude/state/current-task.json` only after the request is specific enough to execute or after you have created the required artifact. If the request is still ambiguous after checking the obvious target files, ask the clarification question first and leave any existing `current-task.json` untouched.
Do not create `.claude/state/`, `.claude/stats/`, scratch files, or placeholder artifacts on a clarification-only path. Clarification-first probing is read-only.
When you do need to persist task state, use `eneo-task-init` / `eneo-task-update`. Do not handcraft JSON with heredocs or raw shell redirection into `.claude/state/current-task.json`.

When you do write state, use this shape:

```json
{
  "slug": "<kebab-slug-inferred-from-description>",
  "lane": "fast|standard|deep",
  "bracket": 1|2|3|4,
  "tenancy_impact": "none|tenant-scoped|cross",
  "audit_impact": "none|appends|schema",
  "status": "in_progress",
  "started_at": "<ISO8601 UTC>",
  "last_update": "<ISO8601 UTC>",
  "next_hint": "<filled per branch below>"
}
```

Use `mktemp + mv` for atomic write.

### 2. Confirm borderline classifications (only when ambiguous)

Only use `AskUserQuestion` when **both** of the following hold:
- LOC estimate is within ±10% of a bracket boundary, OR
- No clear tenancy/audit signal is detectable from the description.

Never prompt when the bracket is obvious.
Never ask a "proceed or spec?" question for an obvious Bracket 1 request unless the user explicitly asked to plan/spec first.

### 3. Branch on lane

#### Fast lane

- **Bracket 1, obvious request** → do not use `AskUserQuestion` unless the request is still ambiguous after inspecting the obvious file(s).

- **If still ambiguous after inspection** → ask one tight clarification question and stop. Do not print the success banner below yet.

- **If actionable after inspection** → make the bounded edit first, then persist state, then print:
  ```
  ✓ Fast lane (<bracket>): <slug>
  Next: /eneo-verify
  ```
  Do not print this success banner before the edit has actually happened.

- **Bracket 2 or user explicitly asks to plan first** → use `AskUserQuestion` once: "Proceed directly, or create a minimal SPEC.md first?" Default: Proceed.

- **Proceed** → set `next_hint` to `/eneo-verify`, print:
  ```
  ✓ Fast lane (<bracket>): <slug>
  Next: edit files directly, then /eneo-verify
  ```
- **Create SPEC** → demote to Standard lane handling below (slug stays the same).

Fast-lane execution rules:
- If the request names a likely artifact (`README`, `docs`, a route, a component, a test, etc.), inspect the most likely target files yourself and make the bounded change without asking the developer to locate it for you.
- When a bounded edit is possible, the order is:
  1. inspect
  2. edit
  3. persist task state
  4. print the success banner + `Next: /eneo-verify`
  Never print the banner before step 2.
- Only ask a follow-up question when multiple plausible targets remain after inspection and choosing the wrong one would be risky.
- Do not end with "Where is it?" for a tiny typo/style fix unless you already checked the obvious file(s) and still cannot disambiguate.
- Respect explicit constraints in `$ARGUMENTS` such as "don't commit", "don't push", or "just triage".
- If you still need clarification after inspecting the obvious file(s), do **not** create or refresh `current-task.json`, do **not** set `next_hint` to `/eneo-verify`, and do **not** print a success banner yet. Ask one tight clarification question and wait.
- For README/docs typo requests, prefer `Read`/`Grep` over shell pipelines. Avoid `mkdir -p` or other setup commands until you know a write will happen.
- Preferred clarification form for tiny typo requests:
  ```
  I checked <file> but couldn't identify the typo confidently. Which line/word should I change?
  ```
- After a successful fast-lane edit, persist state with:
  - `eneo-task-init <slug> fast <bracket> <tenancy_impact> <audit_impact>`
  - `eneo-task-update '.next_hint = "/eneo-verify"'`
  Never emit a raw `tmp=$(mktemp) && cat > "$tmp"` JSON-writing shell block for task state.
- Fast-lane output should stay terse. Preferred shape:
  1. one short line announcing the scan (`Scanning README.md...`)
  2. the edit tool output
  3. one short success block
  Avoid extra narration such as "Let me..." / "Actually..." / "Now persisting state." unless a real branch in behavior occurred.

#### Standard lane

Create `.claude/specs/<slug>/SPEC.md` with exactly these sections, ≤100 lines total:

```markdown
# SPEC: <slug>

## Goal
<1 sentence — what ships when this is done.>

## Acceptance
- <bullet>
- <bullet>

## Files touched
- <path>
- <path>

## Out of scope
- <bullet>
- <bullet>
```

Set `next_hint` to `/eneo-start`. Print:
```
✓ Standard lane: .claude/specs/<slug>/SPEC.md created (<N> lines)
Next: /eneo-start
```

#### Deep lane

Create all of:

1. `.claude/prds/<slug>.md` using the full Section B template (Problem statement / Proposed solution / Success criteria / User stories / Acceptance criteria / Module sketch / Testing decisions / Non-functional requirements / Out of scope / Polishing requirements / Open questions). Include frontmatter with `slug`, `created`, `status: draft`, `tenancy_impact`, `audit_impact`.
2. `.claude/plans/<slug>.md` with only `# Plan: <slug>\n\n<!-- populated by /eneo-plan -->\n`.
3. `.claude/phases/<slug>/` (empty directory).
4. `.claude/context/<slug>-$(date -u +%Y%m%dT%H%M%SZ).md` seed snapshot capturing the current conversation summary.
5. GitHub issue via `gh issue create --label prd,draft --title "PRD: <slug>" --body-file .claude/prds/<slug>.md`. Capture the returned issue number into `current-task.json.prd_issue`.

Set `next_hint` to `/eneo-discuss`. Print:
```
✓ Deep lane: PRD created at .claude/prds/<slug>.md + issue #<NNN>
Next: /eneo-discuss
```

### 4. Final contract

- Every successfully-triaged lane writes a complete `current-task.json` with a populated `next_hint`.
- Clarification-needed fast-lane requests do not mutate or refresh task state until the missing detail is resolved.
- Every branch ends with exactly one `Next: ...` line printed to the developer.
- Stop-hook validator (configured above) runs the appropriate `validate_file_contains.py` call based on the lane; failure re-loops Claude with fix guidance.
- If any step fails (e.g., `gh` not authenticated), print a 3-part error (what / rule / fix) and leave state consistent (rollback partial writes via `mv`).
