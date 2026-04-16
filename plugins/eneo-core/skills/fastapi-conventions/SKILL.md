---
name: fastapi-conventions
description: Use whenever writing or editing any endpoint under backend/src/intric/api/** (and the services those endpoints call). Enforces Eneo's non-negotiable backend invariants — tenant_id filter on every query, audit entry on every mutation, Pydantic v2 response models, SQLAlchemy 2.0 style, structured logging, zero raw SQL. Load this skill before touching any FastAPI router so the patterns are in context.
---

# fastapi-conventions

Eneo's backend is FastAPI + SQLAlchemy 2.0 + Pydantic v2. This skill is the single source of truth for endpoint conventions. The patterns below have invariants enforced by hooks and subagents (`tenancy-checker`, `audit-auditor`); violating them fails `/eneo-verify`.

## The five invariants

1. **Tenancy scoping.** Every query filters by `tenant_id` via the `get_current_tenant` dependency. No exceptions outside explicitly-global tables.
2. **Audit writes.** Every mutation writes `audit_log.create(...)` in the **service layer** (not the router).
3. **Pydantic v2 response models.** Never return raw dicts. Use `response_model=<Schema>` or a typed return.
4. **SQLAlchemy 2.0 style.** `select(Model).where(...)` via `sqlalchemy.select`. No `session.query()`, no raw SQL.
5. **Structured logging.** Use `logger.bind(...)` (structlog-style). `print` is forbidden.

## Router skeleton (copy this, edit the body)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from intric.auth.dependencies import get_current_tenant
from intric.db.dependencies import get_db_session
from intric.domain.api_keys.schemas import RevokeRequest, RevokeResponse
from intric.domain.api_keys.service import APIKeyService
from intric.domain.tenants.types import Tenant

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


@router.post(
    "/{api_key_id}/revoke",
    response_model=RevokeResponse,
    status_code=status.HTTP_200_OK,
)
async def revoke_api_key(
    api_key_id: str,
    body: RevokeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> RevokeResponse:
    service = APIKeyService(session=session)
    try:
        key = await service.revoke(
            tenant_id=tenant.id,
            api_key_id=api_key_id,
            reason=body.reason,
            actor_user_id=tenant.user_id,
        )
    except APIKeyNotFound:
        raise HTTPException(status_code=404, detail="API key not found")
    return RevokeResponse(revoked_at=key.revoked_at)
```

### Why this works

- `get_current_tenant` returns a `Tenant` object including `.id` and `.user_id`. The service receives `tenant_id` as an **argument**, not implicit state.
- Exceptions raised in the service are caught in the router and mapped to HTTP status. The service itself does not know about HTTP.
- `response_model=RevokeResponse` forces Pydantic v2 validation on the way out.

## Service skeleton (where audit writes live)

```python
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from intric.domain.audit.service import AuditLogService
from intric.domain.api_keys.models import APIKey
from intric.domain.api_keys.exceptions import APIKeyNotFound


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
        stmt = select(APIKey).where(
            APIKey.tenant_id == tenant_id,
            APIKey.id == api_key_id,
            APIKey.revoked_at.is_(None),
        )
        result = await self.session.execute(stmt)
        key = result.scalar_one_or_none()
        if key is None:
            raise APIKeyNotFound(api_key_id)

        now = datetime.now(tz=UTC)
        await self.session.execute(
            update(APIKey)
            .where(APIKey.id == api_key_id)
            .values(revoked_at=now, revoked_reason=reason),
        )

        await self.audit.create(
            action="api_key.revoke",
            actor=actor_user_id,
            resource=api_key_id,
            tenant_id=tenant_id,
            metadata={"reason": reason},
        )
        await self.session.commit()
        key.revoked_at = now
        return key
```

### Why

- `tenant_id` is an **explicit argument**. The `tenancy-checker` agent grep's `select(` and verifies `.tenant_id == tenant_id` is present; implicit globals fail the check.
- `AuditLogService` is injected via the session so tests can assert the row via the same session fixture.
- Commits happen at the service boundary, not inside the route.

## Schemas (Pydantic v2, not v1)

```python
from pydantic import BaseModel, Field


class RevokeRequest(BaseModel):
    reason: str = Field(min_length=4, max_length=200)


class RevokeResponse(BaseModel):
    revoked_at: datetime
```

- Use `Field(min_length=..., pattern=r"...")` rather than validators where possible.
- Use `model_config = ConfigDict(extra="forbid")` if strictness matters for the endpoint.

## Common mistakes (and their fixes)

| Mistake | Fix |
|---|---|
| `session.query(APIKey).filter_by(id=...)` | `select(APIKey).where(APIKey.id == ...)` |
| `raw_sql = "SELECT ..."` | Use `select()`; if a CTE is unavoidable, use `sa.text()` bound params |
| `print(f"revoking {id}")` | `logger.bind(api_key_id=id).info("revoke_requested")` |
| `return {"revoked_at": key.revoked_at}` | Define `RevokeResponse`; `response_model=RevokeResponse` |
| `tenant_id = request.state.tenant_id` | `tenant: Tenant = Depends(get_current_tenant)`, pass `tenant.id` explicitly |
| Writing audit in the router | Write audit in the service; router only translates exceptions to HTTP |
| Forgetting a test that queries `audit_log` | Add `assert await audit_log_count(tenant_id=..., action="api_key.revoke") == 1` |

## Pagination

Use the shared `intric.utils.paginate` helper — it returns a typed `Page[Model]` and handles `limit`, `offset`, and `next_cursor` consistently.

## Error handling

Service raises domain-specific exceptions (subclasses of `DomainError`); router catches and maps. Do not leak SQL errors to the HTTP layer.
