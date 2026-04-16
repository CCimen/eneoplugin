---
id: eneo.audit.v1
priority: 0
paths: ["backend/src/intric/audit/**"]
---

# Audit log rules

Loads when editing audit-log code. Compliance treats gaps as P0 incidents.

## Canonical write (service layer only)

```python
await self.audit.create(
    action="<domain>.<verb>",        # e.g. api_key.revoke, user.role_change
    actor=<user_id>,
    resource=<resource_id>,
    tenant_id=<tenant_id>,
    metadata={"reason": reason, ...},  # small, redacted
)
```

- Writes live in the **service**, inside the same transaction as the mutation.
- `action` is dot-notation: `<domain>.<verb>`. New verb → new action name, never overload.
- `metadata` never contains raw PII (emails, personnummer, tokens). Store hashed / redacted values.

## Required test assertion

```python
result = await db_session.execute(
    select(AuditLog).where(
        AuditLog.tenant_id == fixture_tenant.id,
        AuditLog.action == "<domain>.<verb>",
        AuditLog.resource == <resource_id>,
    )
)
rows = result.scalars().all()
assert len(rows) == 1
assert rows[0].metadata["<key>"] == <expected>
```

The `audit-auditor` subagent and `/eneo-verify` Gate 5 check for this shape.

## Schema changes

Any migration altering the `audit_log` table flips `audit_impact` to `schema` and triggers the Deep-lane adversarial review in `/eneo-verify`. Additive-only migrations in a given release; destructive drops use the two-phase migration pattern.

## Retention

Retention is governed by arkivlagen + the Eneo retention policy. Application code does not delete audit rows. Deletion is a separate, compliance-reviewed Alembic migration.
