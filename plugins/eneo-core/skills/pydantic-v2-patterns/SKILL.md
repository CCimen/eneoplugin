---
name: pydantic-v2-patterns
description: Use when creating or modifying any Pydantic model in backend/src/intric/models/** (or adjacent domain/schemas/* files). Enforces Pydantic v2 idioms — model_config over inner Config, @field_validator over root_validator, discriminated unions via Field(discriminator=...), RootModel for top-level containers, TypeAdapter for one-off parsing. Legacy v1 patterns are a code smell the Eneo codebase is actively ratcheting out.
---

# pydantic-v2-patterns

Pydantic v2 is a different runtime from v1 — not a superset. Eneo has a ratchet that forbids new v1 idioms in touched files. This skill is the v2 idiom reference.

## 1. Configure via `model_config`, not inner `Config`

```python
from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    model_config = ConfigDict(
        extra="forbid",           # reject unknown fields
        frozen=True,              # immutable
        populate_by_name=True,    # allow populating by alias or field name
        str_strip_whitespace=True,
    )

    id: str
    email: str
    display_name: str
```

## 2. Validators: `@field_validator` / `@model_validator`

```python
from pydantic import BaseModel, Field, field_validator, model_validator


class TimeRange(BaseModel):
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def must_be_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("start/end must be timezone-aware")
        return v.astimezone(UTC)

    @model_validator(mode="after")
    def check_order(self) -> "TimeRange":
        if self.start >= self.end:
            raise ValueError("start must precede end")
        return self
```

- `mode="before"` gets raw dict — useful for coercion.
- `mode="after"` gets the constructed model — useful for cross-field checks.
- No more `root_validator`, `validator`, `always=True`, `pre=True` — all deprecated.

## 3. Discriminated unions via `Field(discriminator=...)`

```python
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field


class Email(BaseModel):
    kind: Literal["email"] = "email"
    address: str


class SMS(BaseModel):
    kind: Literal["sms"] = "sms"
    number: str


Channel = Annotated[Union[Email, SMS], Field(discriminator="kind")]
```

v2 is strict about discriminator types — all variants MUST use `Literal[...]` for the discriminator field.

## 4. RootModel for top-level lists/dicts

```python
from pydantic import RootModel


class AuditLogBatch(RootModel[list[AuditLogEntry]]):
    """A batch of audit log entries; serializes to a bare JSON array."""
```

Use `.root` to access; no more `__root__` field.

## 5. TypeAdapter for one-off parsing

```python
from pydantic import TypeAdapter

UserList = TypeAdapter(list[User])
users = UserList.validate_python(raw_data)
```

TypeAdapter is faster than `parse_obj_as` and handles generics cleanly.

## 6. Serialization

```python
# Dict: use .model_dump(); NOT .dict()
d = user.model_dump(exclude_none=True, by_alias=True)

# JSON: use .model_dump_json(); NOT .json()
s = user.model_dump_json()

# Construct without validation (internal-only, never on user input):
u = User.model_construct(id="...", email="...", display_name="...")
```

## 7. SQLAlchemy <> Pydantic separation

Keep SQLAlchemy models (`intric/models/sql/`) separate from Pydantic schemas (`intric/models/schemas/` or `domain/*/schemas.py`). Convert explicitly:

```python
def to_schema(row: sql.User) -> User:
    return User.model_validate(row, from_attributes=True)
```

- Use `from_attributes=True` (replaces v1 `orm_mode`).
- NEVER share a class between ORM and API schema; coupling them means a schema change ripples into DB migrations.

## 8. `computed_field` for derived values in the response

```python
from pydantic import BaseModel, computed_field


class APIKey(BaseModel):
    created_at: datetime
    expires_at: datetime

    @computed_field
    @property
    def lifetime_days(self) -> int:
        return (self.expires_at - self.created_at).days
```

## Common v1 → v2 migration traps

| v1 | v2 |
|---|---|
| `class Config: orm_mode = True` | `model_config = ConfigDict(from_attributes=True)` |
| `class Config: allow_population_by_field_name = True` | `populate_by_name=True` |
| `@validator("x", always=True)` | `@field_validator("x")` + default-triggered explicitly |
| `@root_validator` | `@model_validator(mode="after")` |
| `.dict()`, `.json()`, `.parse_obj()` | `.model_dump()`, `.model_dump_json()`, `.model_validate()` |
| `Optional[X] = None` default | same (but `| None` preferred) |
| `class Config: json_encoders = {...}` | `@field_serializer` on the field |
| `parse_obj_as(list[X], data)` | `TypeAdapter(list[X]).validate_python(data)` |
| `__root__` field | `RootModel[...]` |
| `allow_reuse=True` on validator | no longer needed |

## Ratchet-visible issues

The pyright-strict + ruff-check pair flags most v1 idioms automatically in new code. If a touched file still imports `validator`, `root_validator`, or uses `Config`, update the file to v2 as part of the phase (do not leave mixed).
