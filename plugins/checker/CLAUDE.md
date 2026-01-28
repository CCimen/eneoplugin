# Type Checking Guidelines

This project uses Pyright for Python type checking with a ratcheting strategy.

## CRITICAL: Type Check After Every Python Edit

**You MUST follow this workflow when editing Python files in `backend/src/intric/`:**

```
1. Edit file
2. Run typecheck on that file immediately
3. If errors → fix them → run typecheck again
4. Only when clean → continue to next task
```

This is NOT optional. Type errors caught early are easy to fix. Type errors caught at the end (by the Stop hook) mean you've built broken code on top of broken code.

## How to Type Check

After editing a Python file, call the typecheck MCP tool:

```
typecheck(files=["src/intric/path/to/file.py"])
```

The tool shows only NEW errors you introduced (not legacy errors), so the output is always actionable.

## Example Workflow

```
1. You edit src/intric/files/file_service.py
2. You call: typecheck(files=["src/intric/files/file_service.py"])
3. Result shows 2 errors
4. You fix the errors
5. You call typecheck again
6. Result: "No type errors" ✓
7. Now continue to next file or task
```

## Safety Net (Stop Hook)

A Stop hook runs automatically when you finish, checking ALL changed files. This catches anything you missed. But don't rely on it - check as you go for a smoother workflow.

## Manual Check

Run `/checker` to manually check all changed files at any time.

## Ratcheting Strategy

- **New files**: Must pass strict Pyright checks (all errors fail)
- **Modified files**: Only NEW errors (not in baseline) will fail
- **Baseline**: `.pyright-baseline.json` captures known legacy issues

## Configuration

| Environment Variable | Effect |
|---------------------|--------|
| `TYPECHECK_DISABLE=1` | Completely disable type checking |
| `TYPECHECK_WARN_ONLY=1` | Show errors but don't block |
