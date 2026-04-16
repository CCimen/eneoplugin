---
id: eneo.fastapi.v1
priority: 0
paths: ["backend/src/intric/api/**"]
---

# FastAPI endpoint rules

Loads when editing any router under `backend/src/intric/api/**`. Repeats the non-negotiable invariants with actionable specifics so the agent does not need to round-trip to the skill.

## Pattern (copy this when scaffolding a new endpoint)

```python
@router.post("/<resource>/<id>/<verb>", response_model=<ResponseSchema>)
async def <verb>_<resource>(
    <id>: str,
    body: <RequestSchema>,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> <ResponseSchema>:
    service = <Resource>Service(session=session)
    try:
        result = await service.<verb>(
            tenant_id=tenant.id,
            <id>=<id>,
            # ... other args from body
        )
    except <DomainError>:
        raise HTTPException(status_code=<appropriate>, detail="<message>")
    return <ResponseSchema>.model_validate(result, from_attributes=True)
```

## Invariants repeated here (with specifics)

- `response_model=<Schema>` is required. No bare dict returns.
- `tenant: Tenant = Depends(get_current_tenant)` is present on every endpoint touching tenant-scoped data. Pass `tenant.id` to the service **explicitly** — do not read it from `request.state`.
- Service raises domain-specific exceptions (subclasses of `DomainError`). The router maps them to HTTP codes. The service never raises `HTTPException`.
- Audit writes live in the **service layer**, not the router (service shares the session with the audit writer).
- `session.commit()` at the **service boundary**, not inside the route.

## Things that get flagged on PR by `/eneo-verify`

- `@router.post` without a matching `audit_log.create(...)` in the called service.
- `select(<Model>)` without `.where(<Model>.tenant_id == tenant.id)`.
- `session.query(...)` (legacy v1 pattern) — migrate to `select()`.
- `print(...)` — replace with `logger.bind(...).info(...)`.
- Hardcoded `Response(...)` JSON instead of a Pydantic response model.

## Pagination

Use `intric.utils.paginate` — returns typed `Page[Model]` with `limit`, `offset`, `next_cursor`.
