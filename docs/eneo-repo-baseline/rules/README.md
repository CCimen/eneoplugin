# `.claude/rules/` path-scoped rule files

These files live inside **each Eneo clone** at `.claude/rules/`. They're templates — copy them from `docs/eneo-repo-baseline/rules/` in the harness to `.claude/rules/` in your Eneo repo on first setup.

- `eneo-context.md` — always loaded (`paths: ["**/*"]`). Keep it under ~200 lines.
- `fastapi-endpoints.md` — `backend/src/intric/api/**`
- `pydantic-models.md` — `backend/src/intric/models/**`
- `sveltekit-routes.md` — `frontend/apps/web/src/routes/**`
- `alembic-migrations.md` — `backend/alembic/**`
- `audit-log.md` — `backend/src/intric/audit/**`

Every rule file has YAML frontmatter with `id:`, `priority:`, and `paths:`. The `id` + `priority` convention enables a future private overlay to override specific rules without forking (see `docs/FUTURE_PRIVATE_OVERLAY.md`).
