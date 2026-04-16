---
id: eneo.alembic.v1
priority: 0
paths: ["backend/alembic/**"]
---

# Alembic migration rules

Loads when editing migrations. Migrations are unrecoverable in production; discipline is non-negotiable.

## Required per revision

- Both `upgrade()` and `downgrade()` implemented.
- Both tested locally before the PR:
  ```sh
  uv run alembic upgrade head
  uv run pytest backend/tests/db/test_migrations.py
  uv run alembic downgrade -1
  uv run alembic upgrade head
  ```
- If touching `audit_log`, update `.claude/state/current-task.json.audit_impact = "schema"` (the harness `/eneo-ship` validator gates on this tag).
- Destructive drops split into two revisions:
  1. Stop reads/writes in code.
  2. Drop the column in the next release.
- No data migration in the same revision as a schema change.

## SQL style

- Use `op.add_column`, `op.create_index`, `op.execute(sa.text(...))` (for irreducible cases only).
- No inline string SQL; wrap in `sa.text(...)` so parameter binding stays safe.
- Tenant-scoped tables get `NOT NULL tenant_id` + an index on `(tenant_id, <query-key>)` matching existing patterns.

## Commit message prefix

`alembic: <imperative description>` — the staged-commit pattern recognizes the prefix.

## Flagged

- `op.drop_column` without a two-phase plan documented in the PRD.
- Data migration + schema migration in one revision.
- Missing `downgrade()`.
- New tenant-scoped table with no `(tenant_id, ...)` index.
