---
id: eneo.pydantic.v1
priority: 0
paths: ["backend/src/intric/models/**"]
---

# Pydantic model rules (v2)

Loads when editing Pydantic schemas. Pydantic v2 idioms only; Eneo ratchets out v1 patterns on touched files.

## The cheat sheet

| v1 pattern (don't) | v2 replacement |
|---|---|
| `class Config: orm_mode = True` | `model_config = ConfigDict(from_attributes=True)` |
| `class Config: allow_population_by_field_name = True` | `populate_by_name=True` |
| `@validator("x", always=True)` | `@field_validator("x")` |
| `@root_validator` | `@model_validator(mode="after")` |
| `.dict()`, `.json()`, `.parse_obj()` | `.model_dump()`, `.model_dump_json()`, `.model_validate()` |
| `class Config: json_encoders = {...}` | `@field_serializer("...")` |
| `parse_obj_as(list[X], data)` | `TypeAdapter(list[X]).validate_python(data)` |
| `__root__` field | `class Batch(RootModel[list[X]])` |
| `allow_reuse=True` on validator | no longer needed |

## Required on every new model

```python
class <Name>(BaseModel):
    model_config = ConfigDict(
        extra="forbid",              # reject unknown fields unless you have a reason
        str_strip_whitespace=True,
    )
```

## Discriminated unions (required `Literal` tag)

```python
Channel = Annotated[Email | SMS, Field(discriminator="kind")]
```

Where both `Email` and `SMS` declare `kind: Literal["email"|"sms"] = "email"|"sms"`.

## SQLAlchemy <> Pydantic split

Keep ORM models and schema models in separate modules. Convert with:

```python
schema = SchemaModel.model_validate(orm_row, from_attributes=True)
```

Never share a class between ORM and schema layers — a schema change triggers a migration chain otherwise.
