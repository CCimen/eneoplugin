# Type Checking Guidelines

This project uses Pyright for Python type checking with a ratcheting strategy.

## Automatic Type Checking

A Stop hook automatically runs type checking when you finish editing Python files in `backend/src/intric/`. If errors are found, you'll receive feedback and should fix them before continuing.

## Manual Check

Run `/checker` to manually check types at any time.

## Configuration

| Environment Variable | Effect |
|---------------------|--------|
| `TYPECHECK_DISABLE=1` | Completely disable type checking |
| `TYPECHECK_WARN_ONLY=1` | Show errors but don't block |

## Ratcheting Strategy

- **New files**: Must pass strict Pyright checks
- **Modified files**: Only NEW errors (not in baseline) will fail
- **Baseline**: `.pyright-baseline.json` captures known issues
