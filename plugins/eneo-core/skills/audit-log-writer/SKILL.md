---
name: audit-log-writer
description: Use whenever adding or modifying a mutating endpoint (@router.post|put|delete|patch) in backend/src/intric/api/**, or any service method that mutates DB state. Provides the exact audit_log.create template + test assertion template. Eneo's compliance team treats missing audit entries as P0; /eneo-verify's Gate 5 fails ship if an endpoint lacks audit coverage.
---

# audit-log-writer

Every write goes in the audit log. The compliance team (and, downstream, Swedish kommun auditors) rely on this completely. The invariant is enforced by the `audit-auditor` subagent and the audit-completeness gate in `/eneo-verify`.

## The canonical write

Audit entries are written in the **service layer**, not the router, so they always run within the same transaction as the mutation.

```python
from intric.domain.audit.service import AuditLogService


class APIKeyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit = AuditLogService(session)

    async def revoke(
        self,
        *,
        tenant_id: str,
        api_key_id: str,
        reason: str,
        actor_user_id: str,
    ) -> APIKey:
        # ... the mutation ...
        await self.audit.create(
            action="api_key.revoke",          # verb namespace.verb (dot notation)
            actor=actor_user_id,              # the user id performing the action
            resource=api_key_id,              # the resource affected
            tenant_id=tenant_id,              # ALWAYS scoped
            metadata={"reason": reason},      # extra context; keep small
        )
        await self.session.commit()
        # ...
```

## Action naming

Format: `<domain>.<verb>`. Examples:

- `api_key.create`, `api_key.revoke`, `api_key.rotate`
- `user.invite`, `user.deactivate`, `user.role_change`
- `tenant.create`, `tenant.delete`
- `assistant.create`, `assistant.publish`, `assistant.archive`

Do NOT overload one action for multiple verbs. New verb → new action name.

## Metadata: small, stable, redacted

**Include:**
- Fields useful for later forensics (e.g., `"reason": reason`, `"old_role": "viewer"`, `"new_role": "editor"`).
- IDs of related resources if the action affects multiple.

**Exclude:**
- Raw request bodies (often contain PII).
- Email addresses (store user_id; join to `users` table at query time if needed).
- Personnummer / SSN-like strings — NEVER.
- Secrets, tokens, password hashes.

Rule of thumb: if leaking the metadata column would cause a compliance incident, it doesn't belong there.

## Test assertion template

Every endpoint that writes audit must have a test that asserts the row. Use the shared `audit_log_rows` fixture (or equivalent) from `backend/tests/conftest.py`:

```python
import pytest
from sqlalchemy import select

from intric.domain.audit.models.sql import AuditLog


@pytest.mark.asyncio
async def test_revoke_writes_audit(
    client, db_session, fixture_tenant, fixture_api_key
):
    response = await client.post(
        f"/api/v1/api-keys/{fixture_api_key.id}/revoke",
        json={"reason": "rotated"},
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.tenant_id == fixture_tenant.id,
            AuditLog.action == "api_key.revoke",
            AuditLog.resource == fixture_api_key.id,
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].metadata["reason"] == "rotated"
```

This test:

1. Hits the endpoint.
2. Queries the `audit_log` table directly.
3. Asserts exactly one matching row.
4. Verifies at least one metadata field.

The `audit-auditor` subagent looks for this shape in `/eneo-verify` Gate 5.

## Schema-changing migrations (audit_impact = "schema")

If your migration adds/removes/renames a column on `audit_log`:

1. Bump `current-task.json.audit_impact = "schema"` immediately (triggers Deep-lane review).
2. The migration must be backward-compatible for one release (additive only); destructive drops require a two-phase migration.
3. `/eneo-ship` requires `audit:schema` in the PR body; `/eneo-verify`'s adversarial review triggers automatically.

## Do / Don't

| Do | Don't |
|---|---|
| Write audit in the service, inside the same transaction as the mutation | Write audit in the router (can miss if exception propagates) |
| Use dot-notation actions (`api_key.revoke`) | Underscore or camelCase (`api_key_revoke`, `apiKeyRevoke`) |
| Include tenant_id on every call | Omit tenant_id "because it's implicit" |
| Pass actor as user_id | Pass actor as email or session-token |
| Keep metadata small and stable | Dump the whole request body |
| Add a test that queries `audit_log` directly | Rely on an integration framework that infers "an audit was written" |
| Redact PII from metadata | Log raw email/personnummer/tokens |

## When to audit vs. not

Always audit mutations: POST / PUT / DELETE / PATCH that change persistent state.

Don't audit: read endpoints, unauthenticated health checks, internal-only jobs that already write to a job-log table.

Ambiguous cases (e.g., exporting a CSV of tenant data) — default to auditing with `action="<domain>.export"` because export is a compliance-relevant event even though it doesn't mutate the DB.
