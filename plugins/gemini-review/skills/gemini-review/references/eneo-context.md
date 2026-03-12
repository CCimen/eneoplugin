# Eneo Architecture Context for Gemini Reviews

Include relevant sections (not the entire file) in Gemini prompts based on what areas
of the codebase are being touched.

---

## What is Eneo?

Open-source AI platform for the Swedish public sector (built by Sundsvall and Ange
Municipalities). Organizations deploy and manage AI assistants with full data sovereignty.
GDPR/EU AI Act compliant, model-agnostic (OpenAI, Anthropic, Azure, vLLM, local),
multi-tenant with per-org identity federation.

## Project Structure

```
backend/
  src/intric/                    # Main Python package (FastAPI)
    <domain>/                    # Each domain has its own directory
      *_router.py                # FastAPI route handlers
      *_models.py                # Pydantic request/response models
      *_assembler.py             # Domain -> API model conversion
      *_service.py               # Business logic orchestration
      *_repo.py                  # SQLAlchemy repository (data access)
      *_table.py                 # SQLAlchemy table definitions
    main/
      container/container.py     # dependency-injector Container (DI wiring)
      exceptions.py              # Exception hierarchy -> HTTP code mapping
    server/
      routers.py                 # Central router registration with auth guards
      dependencies/container.py  # FastAPI Depends() for Container injection
    authentication/              # JWT, API keys v1/v2, OIDC federation
    audit/                       # Mandatory audit logging (DDD layers)
    spaces/                      # Collaborative workspaces with RBAC
    assistants/                  # AI assistant management
    files/, websites/, info_blobs/  # Knowledge management
    worker/                      # ARQ background workers

frontend/
  apps/web/                      # SvelteKit application (TypeScript, Tailwind)
  packages/
    intric-js/                   # Auto-generated TypeScript API SDK
    ui/                          # Shared Svelte component library
```

## Service Layer Pattern

All business logic follows: **Router -> Service -> Repository -> Table**

```python
# Router: HTTP concerns only
@router.post("/things", response_model=ThingPublic, status_code=201)
async def create_thing(
    payload: CreateThingRequest = Body(...),
    container: Container = Depends(get_container(with_user=True)),
):
    service = container.thing_service()
    return await service.create(payload)

# Service: Business logic, validation, audit logging. No HTTP concepts.
class ThingService:
    def __init__(self, repo, audit_service, user):
        ...
    async def create(self, request):
        thing = await self.repo.create(...)
        await self.audit_service.log_async(...)
        return thing

# Repository: Data access. SQLAlchemy async queries only.
class ThingRepository:
    def __init__(self, session: AsyncSession):
        ...
```

## Dependency Injection

Uses `dependency-injector` with a central `Container` class:

```python
class Container(containers.DeclarativeContainer):
    session = providers.Dependency(instance_of=AsyncSession)
    user = providers.Dependency(instance_of=UserInDB)
    thing_repo = providers.Factory(ThingRepository, session=session)
    thing_service = providers.Factory(ThingService, repo=thing_repo, ...)
```

Router gets container via: `container: Container = Depends(get_container(with_user=True))`

## Authentication and Authorization

### Auth Mechanisms
1. **JWT Bearer tokens** (OIDC) — RS256/HS256, claims: sub, username, aud, iat, exp, iss
2. **OIDC Federation** — MobilityGuard, Entra ID, generic OIDC
3. **API Keys** — v1 (legacy SHA-256) and v2 (full lifecycle with scopes/permissions)

### API Key v2 System
- `scope_type`: tenant | space | assistant | app (hierarchical containment)
- `permission`: read | write | admin
- `resource_permissions`: per-resource-type overrides
- `state`: active | suspended | revoked | expired
- Features: rate limiting, allowed origins, allowed IPs, expiry, rotation

### Auth Guards (applied at router level in server/routers.py)

```python
# Method-based: GET=read, POST/PUT/PATCH=write, DELETE=admin
Depends(require_resource_permission_for_method("spaces"))

# Scope check: API key must cover this resource
Depends(require_api_key_scope_check(resource_type="space", path_param="id"))

# Explicit permission level
Depends(require_api_key_permission(ApiKeyPermission.ADMIN))

# Role-based user permission
Depends(require_permission(Permission.ADMIN))
```

### Permission Hierarchy
`read` < `write` < `admin`

Method mapping: GET/HEAD/OPTIONS -> read, POST/PUT/PATCH -> write, DELETE -> admin

## Audit Logging (MANDATORY)

All new features MUST include audit logging. Uses `AuditService.log_async()` for
non-blocking writes via ARQ worker.

```python
await audit_service.log_async(
    tenant_id=user.tenant_id,
    actor_id=user.id,
    action=ActionType.THING_CREATED,
    entity_type=EntityType.THING,
    entity_id=thing.id,
    description=f"Created thing '{thing.name}'",
    metadata=AuditMetadata.standard(actor=user, target=thing),
)
```

Key types:
- `ActionType` enum — ~80 distinct actions (admin, user, security, integration, system)
- `EntityType` enum — all auditable entity types
- `AuditMetadata` builders: `.standard()`, `.multi_target()`, `.system_action()`, `.authentication()`, `.minimal()`

## Exception Handling

Custom exceptions in `main/exceptions.py` auto-mapped to HTTP responses:

| Exception | HTTP Code |
|-----------|-----------|
| `NotFoundException` | 404 |
| `UnauthorizedException` | 403 |
| `AuthenticationException` | 401 |
| `BadRequestException` | 400 |
| `ValidationException` | 422 |
| `UniqueException` | 400 |
| `NameCollisionException` | 409 |

Error response format:
```json
{"code": "resource_not_found", "message": "API key not found."}
```

For API key errors: `ApiKeyValidationError(code=..., message=..., status_code=...)`

## API Conventions

- All routes under `/api/v1/`
- OpenAPI docs at `/docs`
- Cursor-based pagination: `limit`, `cursor` (datetime), `previous` (bool)
- Response: `items`, `limit`, `next_cursor`, `previous_cursor`, `total_count`
- Response models: `*Public` suffix (e.g., `SpacePublic`)
- Request models: `Create*Request`, `Update*Request`
- Tags group related endpoints
- Always include `summary`, `description`, `responses` with examples

## Pydantic V2 Patterns

```python
from pydantic import BaseModel, Field, ConfigDict

class ThingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str = Field(..., description="Human-readable name")
    created_at: datetime
```

## SQLAlchemy Async ORM

```python
from intric.database.tables.base_class import BasePublic

class ThingTable(BasePublic):
    __tablename__ = "things"
    name = Column(String, nullable=False)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"))
```

Base classes: `BasePublic` (UUID id + timestamps + auto tablename), `TimestampMixin`, `IdMixin`

Database: PostgreSQL with `asyncpg`, `pgvector` for semantic search.

## Type Checking

- Pyright with ratcheting baseline (only NEW errors reported)
- Run after every Python edit in `backend/src/intric/`
- Strict mode for new files, baseline mode for existing files

## Frontend Patterns

- **SvelteKit** with TypeScript
- **Tailwind CSS** for styling
- **Paraglide i18n**: `sv.json` and `en.json` must stay in sync
- After translation changes: `cd frontend/apps/web && bun run i18n:compile`
- **intric-js** SDK wraps all backend API calls with typed methods
- Auth flow: JWT cookies checked in `hooks.server.ts`
- Supports Zitadel, MobilityGuard, generic OIDC identity providers

## Testing Patterns

- **pytest** with `asyncio_mode = auto`
- Unit tests: `AsyncMock` repos, direct service instantiation
- Integration tests: `testcontainers` (real PostgreSQL + Redis)
- Markers: `integration`, `migration_isolation`
- VCR cassettes for HTTP mocking
