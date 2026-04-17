---
description: Ratchet gate for the current phase — pyright strict, pytest, coverage, mutation ≥70%, audit-log completeness, tenancy smoke, conditional adversarial review on risky paths. Streams each gate as it runs.
argument-hint: "[<phase-number>]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Task
  - Bash(uv *)
  - Bash(bun *)
  - Bash(jq *)
  - Bash(git *)
model: sonnet
---

# /eneo-verify

Run seven quality gates on the current phase. Stream each gate's result as it completes (don't batch). Write evidence to `.claude/phases/<slug>/phase-<NN>-verify.md` and set `current-task.json.next_hint = "/eneo-commit"` on success.

Every `eneo_exec` call is wrapped through the shared env library so dual-mode (host/in-container) works uniformly.

## Pre-flight

- Determine slug (from `current-task.json.slug`) and phase (from `$ARGUMENTS` or `current-task.json.phase`). Missing → print `Next: /eneo-start` and exit.
- Source `lib/env.sh` and `lib/state.sh`.

## Streaming gate execution

Run gates in order. For each gate, print the line on start (`… running`), then overwrite/append the result on completion with `✓` or `✗`. Three-part error on failure.

### Gate 1 — pyright strict

```
… gate 1/7: pyright --strict on changed files
```

Run `eneo_exec "backend" uv run pyright --strict --outputjson $(changed .py files)`. Parse errors.

- ✓ `pyright strict: 0 errors on <N> changed files`
- ✗ `pyright strict: <N> errors.`
  - Rule: pyright ratchet (.claude/rules/eneo-context.md#pyright-strict).
  - Fix: resolve errors printed below. Re-run `/eneo-verify` when clean.

### Gate 2 — pytest

```
… gate 2/7: pytest
```

Run `eneo_exec "backend" uv run pytest -q --cov --cov-report=json:.claude/ratchet/.current/coverage.json` plus frontend `eneo_exec "frontend/apps/web" bun run test`.

- ✓ `pytest: <P> passed, <S> skipped, 0 failed`
- ✗ `pytest: <F> failed. Fix the listed tests; do not modify them (phase-gate will block anyway if we're in GREEN).`

### Gate 3 — coverage ratchet

```
… gate 3/7: coverage ratchet
```

Refresh `.claude/ratchet/.current/coverage.json`, then invoke `eneo-ratchet-check --coverage .claude/ratchet/coverage.json --mutation /dev/null --repo-root . --current-coverage .claude/ratchet/.current/coverage.json`. The validator compares committed baselines against the current artifact; if the artifact is missing during a verified phase, the ratchet fails loudly instead of silently passing.

- ✓ `coverage: no regressions`
- ✗ `coverage regression on <path>: floor <X>%, actual <Y>%.`
  - Fix: add tests until the file meets the floor, then re-run `/eneo-verify`.

### Gate 4 — mutation score

```
… gate 4/7: mutation score (floor 70%)
```

Run `eneo_exec "backend" uv run mutmut run --paths-to-mutate src/intric/<changed_modules>` and write `.claude/ratchet/.current/mutation.json`, then invoke the ratchet validator with `--current-mutation .claude/ratchet/.current/mutation.json`.

- ✓ `mutation: <S>% (floor 70%)`
- ✗ `mutation: <S>% below floor 70%.`
  - Fix: `eneo_exec backend uv run mutmut results` to see surviving mutants; strengthen assertions.

### Gate 5 — audit-log completeness

```
… gate 5/7: audit-log completeness on touched endpoints
```

Grep changed files for `@router.(post|put|delete|patch)`. For each match, verify a call-graph path to `audit_log.create(...)` AND a test under `backend/tests/` that asserts the audit row. Run the `audit-auditor` subagent for deep verification.

- ✓ `audit-log: <N> mutating endpoints, all covered`
- ✗ `audit-log: <path>:<line> missing audit entry OR missing test assertion.`
  - Rule: every mutating endpoint writes an audit row and its test asserts the row (.claude/rules/audit-log.md).
  - Fix: add `audit_log.create(...)` in the service layer + a test that queries the audit table.

### Gate 6 — tenancy isolation smoke test

```
… gate 6/7: tenancy isolation smoke
```

Run the Eneo `tenant_leak` contract test via `eneo_exec "backend" uv run pytest tests/contract/test_tenant_isolation.py`.

- ✓ `tenancy: no cross-tenant leak`
- ✗ `tenancy leak detected: <test> failed.`
  - Rule: every query scoped via `get_current_tenant()` (.claude/rules/eneo-context.md#tenancy).
  - Fix: add the tenant filter to the leaking query; re-run.

### Gate 7 — conditional adversarial review

Read `current-task.json.audit_impact`, `.tenancy_impact`, and the phase LOC delta. **Only** trigger review when ANY of:

- `audit_impact == "schema"`
- `tenancy_impact == "cross"`
- LOC > 800 for the phase
- PR labels contain `authz`

If skipped, print `gate 7/7: adversarial review skipped — change is low-risk`.

If triggered, spawn three fresh-context judges (`autoreason-judge` × 3) with A/B/AB incumbent / adversarial / synthesis per Section E. Blind Borda ranking. "Do nothing" is a first-class outcome.

- ✓ `adversarial review: incumbent A wins Borda <x>-<y>-<z>; no changes proposed`
- ✓ `adversarial review: synthesis AB wins; <M> suggested edits — applied to the phase`
- ✗ `adversarial review: block — <reason>`.

## Evidence file

Write `.claude/phases/<slug>/phase-<NN>-verify.md` with the streamed log verbatim (command outputs included) — this is the SuperClaude "Four Questions" evidence required by `/eneo-commit` and `/eneo-ship`.

## Final output

```
✓ All gates pass. Phase <N> verified.
  Evidence: .claude/phases/<slug>/phase-<NN>-verify.md
  Next: /eneo-commit
```

Set `current-task.json.next_hint = "/eneo-commit"` and status `verified`.

On any gate failure: set `status = "blocked"` with the failing gate in `next_hint`; do NOT proceed. Let the developer fix and re-run.
