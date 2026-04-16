# Eneo / intric — agent rules

## Setup (run once per clone)

If `/plugin list` does not show `eneo-core`, run:

  /plugin marketplace add eneo-ai/eneo-agent-harness
  /plugin install eneo-core@eneo-agent-harness
  /plugin install eneo-standards@eneo-agent-harness
  /plugin install eneo-findings@eneo-agent-harness
  # optional external reviewers:
  /plugin install eneo-review@eneo-agent-harness

Then run `/eneo-doctor` to verify the environment.

## Non-negotiable invariants

1. Every mutating endpoint writes an audit entry. Verified by tests.
2. Every DB query filters by `tenant_id` via `get_current_tenant()`. No exceptions.
3. Pyright strict: zero new errors on touched files (ratchet in `.claude/ratchet/`).
4. Mutation score ≥ 70% on changed `intric/` modules.

## Forbidden

- Raw SQL strings. Use SQLAlchemy 2.0 `select()` style.
- `print`. Use structured logging.
- Bypassing `get_current_tenant()`.
- Editing tests during GREEN phase (hook blocks).
- Editing src/ during RED phase (hook blocks).

## Workflow

/eneo-new picks the lane and creates the right artifact. Then:

- Fast:     /eneo-new (choose "proceed") → edit → /eneo-verify → /eneo-ship
- Standard: /eneo-new → /eneo-start → /eneo-verify → /eneo-ship
- Deep:     /eneo-new → /eneo-discuss → /eneo-plan →
            /eneo-start (per phase) → /eneo-verify → /eneo-ship → /eneo-recap

/eneo-start resumes whichever plan you're in — no args in the common case.
/eneo-doctor when anything feels off; it prints fixes.
/fewer-permission-prompts after a few sessions to tune the allowlist from real usage.
One workflow per session. Start fresh for new milestones.

Built-in `/recap` is session scope. `/eneo-recap` is milestone scope.

## Imports

@.claude/rules/eneo-context.md
