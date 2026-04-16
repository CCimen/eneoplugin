---
description: Turn an approved PRD into a tracer-bullet phased plan (Pocock template). Phase 1 is always the thinnest end-to-end path; phase count 3–6. Stop-hook validator enforces required sections.
argument-hint: "[<slug>]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
model: opus
hooks:
  Stop:
    - hooks:
        - type: command
          command: >-
            bash -c '
              SLUG=$(jq -r ".slug // empty" "$CLAUDE_PROJECT_DIR/.claude/state/current-task.json" 2>/dev/null);
              if [[ -n "$SLUG" && -f "$CLAUDE_PROJECT_DIR/.claude/plans/$SLUG.md" ]]; then
                python3 "${CLAUDE_PLUGIN_ROOT:-$CLAUDE_PROJECT_DIR/plugins/eneo-standards}/hooks/validators/validate_file_contains.py" \
                  --file ".claude/plans/$SLUG.md" \
                  --contains "## Phase 1: Tracer Bullet" \
                  --contains "## Out of scope" \
                  --contains "PRD:" \
                  --contains "Wave plan:";
              fi
            '
---

# /eneo-plan

Produce `.claude/plans/<slug>.md` from the PRD. Phase 1 is mandatory tracer bullet. The Stop-hook validator (configured above) fails the command if any required section is missing — Claude re-loops on stderr.

## Pre-flight

- Determine slug (from `$ARGUMENTS` or `current-task.json.slug`). Missing slug → print `Next: /eneo-new "<description>"` and exit.
- Verify `.claude/prds/<slug>.md` exists. If not → `Next: /eneo-new <slug>`.
- Verify `current-task.json.lane == "deep"` — Standard lane does not use `/eneo-plan`.

## Plan template

Every phase uses this block verbatim (Pocock prd-to-plan + Kiro tasks.md fusion). Phase 1 tracer bullet always touches schema + service + API route + SvelteKit minimal UI + 1 integration test:

```markdown
# Phase <N> — <short name>
**PRD:** @.claude/prds/<slug>.md#us-<story-id>   <!-- must cite at least one user story -->
**Goal:** <thin end-to-end slice>

**Wave plan:**
- Wave 1 (parallel): schema draft, API contract draft, test skeleton
- Wave 2 (parallel, depends on W1): backend impl, frontend impl, migration
- Wave 3 (serial): integration + audit-log verification

**Deliverables:**
- [ ] <schema change> (files: <tbd>)
- [ ] <service> passing pyright strict
- [ ] <route> with authz test
- [ ] Alembic migration up/down tested
- [ ] Audit entries appearing for mutating endpoints

**Done when:** <specific observable outcome>
**Mutation-score floor:** 70% on changed `intric/<module>/` files
```

## Required sections (validated by Stop-hook)

The generated plan file must contain:

- `## Phase 1: Tracer Bullet` (literal heading; Phase 1 is non-negotiable)
- `## Out of scope` (per playbook Section B discipline rule 2)
- `PRD:` reference in every phase body
- `Wave plan:` header in every phase body

Also enforce the discipline rules from Section B at write-time (not by validator, because validator is line-oriented):

- Every KPI contains a number or a concrete command (e.g. `pyright --strict`).
- No file paths in Module sketch (Pocock rule; they rot fast).

## Wave-plan guardrails

Per Section H anti-pattern table, reject a wave plan where:

- **Over-parallelization.** Waves with >5 parallel tasks for a single-context feature → reduce to serial.
- **Shared-file race.** Two agents in the same wave claim overlapping `files:` → forbid and print which files collide.

## Agent dispatch

Optionally spawn `planner` and `architect` subagents (if present) to draft the wave table for each phase in parallel. The outputs feed back into this command for final stitching.

## DX output

Stream as phases are drafted:

```
✓ Phase 1: Tracer Bullet — 5 deliverables, 3 waves
✓ Phase 2: UI polish + list view — 4 deliverables, 2 waves
✓ Phase 3: Audit entries + email — 3 deliverables, 1 wave
```

On success (Stop validator passes), print:

```
✓ Plan saved with <N> phases to .claude/plans/<slug>.md
  PRD: @.claude/prds/<slug>.md (unchanged)
  Next: /eneo-start
```

On validator failure, the hook surfaces stderr to Claude; Claude re-edits the plan to add missing sections. Do not work around validator failure — fix the plan.
