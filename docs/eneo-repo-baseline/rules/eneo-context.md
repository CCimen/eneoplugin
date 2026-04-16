---
id: eneo.context.v1
priority: 0
paths: ["**/*"]
---

# Eneo core context

Loaded on every session. Capped at ~200 lines so the token budget stays bounded; specialized rule files live next to this one and load only when their paths match the current edit.

## Non-negotiable architectural invariants

1. **Audit logging on every write.** Every mutating endpoint (`@router.post | put | delete | patch`) writes an `audit_log.create(...)` in the service layer. Tests query the `audit_log` table to assert the row exists. The `audit-auditor` subagent enforces; `/eneo-verify` Gate 5 blocks ship on gaps.
2. **Tenancy via `tenant_id` on every query.** Every `select(Model)` uses `.where(Model.tenant_id == tenant.id)` where `tenant = Depends(get_current_tenant)`. The `tenancy-checker` subagent enforces.
3. **SvelteKit routes use typed load functions.** `+page.server.ts` exports `export const load: PageServerLoad`; form actions for all mutations; `$env/static/private` only imported in `.server.ts` files.

## Forbidden patterns

- **Raw SQL strings** in app code. SQLAlchemy 2.0 `select()` only. (Alembic migrations may use `sa.text()` for irreducible cases.)
- **`print`.** Use structlog-style structured logging with `logger.bind(...)`.
- **Bypassing `get_current_tenant()`.** The tenant object flows explicitly; never read `request.state.tenant` directly.
- **Raw hardcoded URLs** to the backend in SvelteKit code. Route through `$lib/api`.
- **PII in logs.** Redact emails / personnummer / tokens to hash prefixes.

## TDD phase machine (see Section D)

The `phase-gate.sh` hook reads `.claude/state/phase`:

- `RED` — tests only in `backend/tests/`; src edits under `backend/src/intric/` are blocked
- `GREEN` — src edits only; test edits are blocked
- `REFACTOR` — both unlocked; reviewer + integrator wave
- `FREE` — no restrictions (no active phase)

`/eneo-start` toggles the phase per wave. Emergency override via `/eneo-start <slug> --phase <red|green|refactor|free>`.

## Karpathy principles — each paired with an enforcement hook

| Principle | Enforcement |
|---|---|
| Think Before Coding | `/eneo-discuss` confidence gate (blocks at <70%) |
| Simplicity First | LOC-delta check in `/eneo-verify` warns if delta > plan estimate × 1.5 |
| Surgical Changes | Pre-commit hook rejects commits that touch files not listed in the phase's declared `files:` field |
| Goal-Driven Execution | Every phase has a machine-checkable `Done when:` clause verified by `/eneo-verify` |

The principles are aspirational without the hooks. Keep the hooks current — if one drifts, the principle it pairs with silently stops being enforced.

## Swedish public-sector compliance

- Frontend labels are Swedish by default (`sv-SE`). Use `$lib/i18n` where the team has adopted it.
- GDPR: audit-log metadata must not contain raw PII. Store user IDs; join at query time.
- Arkivlagen (archive law) — audit log rows are retained per the retention policy; never deleted by application code. Deletion is a separate Alembic migration reviewed by compliance.
- WCAG 2.1 AA — every interactive element has an accessible name; keyboard navigation; ≥4.5:1 contrast for normal text.

## Path-scoped specialized rules

These files load only when editing matching paths:

- `@.claude/rules/fastapi-endpoints.md` — `backend/src/intric/api/**`
- `@.claude/rules/pydantic-models.md` — `backend/src/intric/models/**`
- `@.claude/rules/sveltekit-routes.md` — `frontend/apps/web/src/routes/**`
- `@.claude/rules/alembic-migrations.md` — `backend/alembic/**`
- `@.claude/rules/audit-log.md` — `backend/src/intric/audit/**`

When Claude's current edit matches one of the paths, the specialized rule loads on top of this file.
