# Type Checking Guidelines

This project uses Pyright for Python type checking with a ratcheting strategy.

## Proactive Type Checking (MCP Tool)

**Use the `typecheck` tool PROACTIVELY** after editing Python files in `backend/src/intric/`. Don't wait for the Stop hook - check files immediately after editing to catch errors early.

```
typecheck(files=["src/intric/files/file_service.py"])  # Check specific file
typecheck(files=[])                                      # Check all changed files
```

The tool respects ratcheting - you'll only see NEW errors you introduced, not legacy errors.

## Automatic Safety Net (Stop Hook)

A Stop hook automatically runs when you finish editing, checking ALL changed Python files. If errors are found, you'll receive feedback and must fix them before continuing.

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
