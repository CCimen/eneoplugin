# Eneo harness state schema

`.claude/state/current-task.json` is the shared source of truth that every hook, every `/eneo-*` command, `/eneo-doctor`, and the status line read and write. Design it once; read it from everywhere else.

## Shape

```json
{
  "slug": "revoke-api-keys",
  "lane": "deep",
  "bracket": 4,
  "tenancy_impact": "tenant-scoped",
  "audit_impact": "appends",

  "phase": 2,
  "phase_total": 3,
  "phase_name": "backend + frontend impl",
  "tdd_phase": "GREEN",

  "wave": 2,
  "wave_total": 3,
  "wave_status": { "1": "done", "2": "in_progress", "3": "pending" },
  "active_agents": ["tdd-impl-writer", "sveltekit-specialist"],

  "status": "in_progress",
  "started_at": "2026-04-16T12:30:00Z",
  "last_update": "2026-04-16T12:42:18Z",
  "next_hint": "/eneo-verify",

  "prd_issue": 1234,
  "last_pr": 5678
}
```

## Field reference

| Field | Type | Writer | Notes |
|---|---|---|---|
| `slug` | string | `/eneo-new` | Kebab-case; unique across in-flight plans. |
| `lane` | `"fast"\|"standard"\|"deep"` | `/eneo-new` | Section A classification. |
| `bracket` | 1–4 | `/eneo-new` | Section A bracket. |
| `tenancy_impact` | `"none"\|"tenant-scoped"\|"cross"` | `/eneo-new` | Echoed on PR body; validated by `pr_metadata_check`. |
| `audit_impact` | `"none"\|"appends"\|"schema"` | `/eneo-new` | Same as above. |
| `phase` | integer \| null | `/eneo-plan` writes once; `/eneo-start` updates | Null until planning completes (Fast lane may stay null). |
| `phase_total` | integer \| null | `/eneo-plan` | Total phases in the plan. |
| `phase_name` | string \| null | `/eneo-plan` | Short name of the current phase. |
| `tdd_phase` | `"RED"\|"GREEN"\|"REFACTOR"\|"FREE"` | `/eneo-start`, or `/eneo-start <slug> --phase <x>` | Mirrored into `.claude/state/phase` for hook compatibility. |
| `wave` | integer \| null | `/eneo-start` | Current wave within the phase. |
| `wave_total` | integer \| null | `/eneo-start` | Total waves in the phase. |
| `wave_status` | object | `/eneo-start` + `wave-barrier.sh` | `{ "1": "done", "2": "in_progress", "3": "pending" }`. |
| `active_agents` | string[] | `/eneo-start` sets; `wave-barrier.sh` removes one returning agent at a time | Empty when idle. Duplicate names are allowed when a wave intentionally dispatches multiple agents of the same type. |
| `status` | `"in_progress"\|"blocked"\|"verified"\|"done"` | any command | Coarse lifecycle. `verified` is the gate-passed state consumed by `/eneo-commit` and `/eneo-ship`; `done` is terminal and normally reached just before `/eneo-recap` clears state. |
| `started_at` | ISO8601 | `/eneo-new` | Immutable after creation. |
| `last_update` | ISO8601 | every writer | Updated on every write via `date -u +%Y-%m-%dT%H:%M:%SZ`. |
| `next_hint` | string | every successful command | The `Next:` line the status line / terminal should display. |
| `prd_issue` | integer | `/eneo-new` (Deep) | GitHub issue number of the PRD. |
| `last_pr` | integer | `/eneo-ship` | Most recently opened PR. |

## Write invariants

- Only `/eneo-new` **creates** the file (via `eneo_task_init` in `lib/state.sh`).
- Only `/eneo-recap` **deletes** it (via `eneo_task_clear`).
- **Every other writer goes through `eneo_task_update`** from `plugins/eneo-standards/hooks/lib/state.sh`. The helper takes a jq expression, applies it atomically (`mktemp + mv`), and sets `last_update` automatically. This centralizes the atomic-swap pattern AND prevents schema drift between commands and hooks (e.g. one writer emitting `wave_status` as an object, another as an array).
- `plugins/eneo-standards/hooks/lib/state.sh` serializes writes with a directory lock under `.claude/state/.locks/`. `wave-barrier.sh` uses the same lock so parallel `SubagentStop` events cannot lose increments. Locks older than 30 seconds are treated as stale and reclaimed automatically.
- Every reader uses `jq -re` (or `eneo_task_get` from `state.sh`) with a safe default. A malformed state file never hard-fails a read; the status line silently shows line 1 only, hooks exit 0.
- The phase mirror at `.claude/state/phase` is written only via `eneo_phase_set` which updates the JSON first and the mirror second, so a race leaves the JSON authoritative.

## Helper API (`plugins/eneo-standards/hooks/lib/state.sh`)

```bash
eneo_task_init <slug> <lane> <bracket> <tenancy_impact> <audit_impact>   # /eneo-new only
eneo_task_clear                                                          # /eneo-recap only
eneo_task_update '<jq-expression>' [arg-name arg-value]...               # everyone else
eneo_task_get    '<jq-expression>'                                       # read

eneo_phase_set   RED|GREEN|REFACTOR|FREE                                 # writes JSON + mirror
eneo_next_hint_consume                                                   # reads next_hint and clears it atomically
```

`eneo_task_update` takes additional `--arg` pairs so jq expressions can reference user-supplied values safely (no shell interpolation into the jq program). Prefix an arg name with `json:` to pass it through `--argjson` instead of `--arg`. Example from `wave-barrier.sh`:

```bash
eneo_task_update \
  '.wave_status = ((.wave_status // {}) | .[($__wave|tostring)] = "done") | .active_agents = []' \
  __wave "$WAVE_NO"
```

Example with typed JSON:

```bash
eneo_task_update \
  '.active_agents = $__agents | .wave_status = ((.wave_status // {}) | .["1"] = "in_progress")' \
  json:__agents '["tdd-test-writer","architect"]'
```

## Readers

| Reader | Uses |
|---|---|
| `plugins/eneo-standards/hooks/phase-gate.sh` | `.claude/state/phase` (mirror of `tdd_phase`). |
| `plugins/eneo-standards/hooks/bash-firewall.sh` | Same mirror. |
| `plugins/eneo-standards/hooks/wave-barrier.sh` | Reads and writes `wave`, `wave_status`, `active_agents`. |
| `plugins/eneo-standards/hooks/user-prompt-audit.sh` | Reads `slug` for the audit line; updates `last_update`. |
| `plugins/eneo-standards/hooks/session-start-context.sh` | Reads whole file to print session context. |
| `plugins/eneo-standards/statusline/eneo-statusline.sh` | Reads everything for line 2 rendering. |
| `/eneo-doctor` | Detects stale state file (points to missing plan → suggest `rm`). |
| `/eneo-start`, `/eneo-verify`, `/eneo-commit`, `/eneo-ship`, `/eneo-recap` | Primary writers. |

## Phase-state mirror file

`.claude/state/phase` is a single-word file (`RED|GREEN|REFACTOR|FREE`) that duplicates `current-task.json.tdd_phase`. This redundancy is deliberate: shell hooks that would otherwise need `jq` can do `cat .claude/state/phase` for sub-millisecond reads on every PreToolUse. The mirror is always written *after* the JSON update so a race leaves the JSON authoritative. Direct edits to the mirror are blocked; use `eneo_phase_set` instead.
