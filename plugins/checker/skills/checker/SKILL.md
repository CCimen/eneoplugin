---
name: checker
description: Run Pyright type checking on Python files. Use after making changes to backend/src/intric/**/*.py, before committing, or when you want to verify type safety.
disable-model-invocation: true
---

# Type Checker

Run type checking for the eneo backend Python codebase.

## Command

```bash
cd "$CLAUDE_PROJECT_DIR/backend" && ./scripts/typecheck_changed.sh
```

## How It Works

The type checker uses a **ratcheting strategy**:
- **New files**: Strict Pyright checking (all type errors must pass)
- **Existing files**: Basic checking with baseline comparison (only NEW errors fail)

This prevents regression while not requiring fixes to legacy code.

## Interpreting Output

### Success
```
No Python files to check.
```

### Errors
Errors show: `file:line:col: severity[rule]: message`

Example:
```
src/intric/files/file_service.py:42:5: error[reportOptionalMemberAccess]: "id" is not a known attribute of "None"
```

## Fixing Common Errors

1. **reportOptionalMemberAccess**: Add null checks or use `assert x is not None`
2. **reportAttributeAccessIssue**: Check method/attribute name spelling
3. **reportArgumentType**: Fix function argument types
4. **reportUndefinedVariable**: Import missing names or fix typos

## When to Run

- After editing Python files in `backend/src/intric/`
- Before committing changes
- When the Stop hook reports errors
