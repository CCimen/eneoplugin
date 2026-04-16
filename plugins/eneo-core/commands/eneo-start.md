---
description: Resume the current plan and run its next incomplete phase via Wave → Checkpoint → Wave. Smart defaults; only prompts when there is real ambiguity. Emergency phase override via --phase.
argument-hint: "[<slug>] [<phase-number> | --phase <red|green|refactor|free>]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
  - AskUserQuestion
  - Bash(git *)
  - Bash(uv *)
  - Bash(bun *)
  - Bash(pytest *)
  - Bash(pyright *)
  - Bash(jq *)
model: sonnet
---

# /eneo-start

One command for resuming work and orchestrating parallel wave execution. Do the obvious thing. Only prompt when there's real ambiguity.

## Argument resolution

Parse `$ARGUMENTS` into `slug`, `phase_number`, and `--phase <value>`.

### Emergency phase override

If `--phase <red|green|refactor|free>` is present (with or without slug):

1. Determine slug (arg → `current-task.json.slug` → fail with `Next: /eneo-new "<description>"`).
2. Call `eneo-phase-set <VALUE>` (writes both JSON and mirror atomically).
4. Print:
   ```
   ✓ TDD phase for <slug> → <VALUE>
     Next: /eneo-start (resume from phase state, do not re-dispatch agents)
   ```
5. Exit.

### Smart defaults (no override)

| Situation | Action |
|---|---|
| No args + current slug + next incomplete phase | Resume silently. Print `Resuming <slug> phase <N>/<total>.` |
| No args + multiple in-flight plans, no current slug | Use `AskUserQuestion` to pick; default-highlight most-recently-modified plan |
| No args + no in-flight plans | Print `No in-flight plans. Next: /eneo-new "<description>"` and exit |
| `<slug>` | Resume that slug at next incomplete phase |
| `<slug> <N>` | Jump to phase N |

## Wave → Checkpoint → Wave orchestration

Once a phase is selected, run it per playbook Section F. Stream progress at every transition (Section F DX rule 6, "Stream progress; don't batch").

### 1. Phase header (one-line)

```
Phase <N>/<total>: <phase_name>
```

### 2. Dependency graph (one-time render per phase)

Render the barkain-style ASCII wave graph from the phase file. Example:

```
Wave 1 (parallel)    Wave 2 (parallel)         Wave 3 (serial)
┌─ researcher ─┐      ┌─ backend-dev ──┐
├─ architect  ─┤ ───► ├─ frontend-dev ─┤ ────► ┌─ integrator ─┐
└─ security   ─┘      └─ db-migrator  ─┘        └─ reviewer   ─┘
```

### 3. Seed wave state (before each wave fires)

Via `eneo_task_update` and by writing `.claude/state/wave.json`:

```bash
echo '{"wave":1,"expected":<N>,"done":0,"status":"in-progress"}' > .claude/state/wave.json
eneo_task_update '.wave = $__w | .wave_total = $__t | .active_agents = $__a | .wave_status = ((.wave_status // {}) | .["1"] = "in_progress") | .next_hint = null' \
  __w 1 __t "<total_waves>" json:__a '["tdd-test-writer","architect",...]'
```

Also call `eneo_phase_set RED` for Wave 1, `GREEN` for Wave 2, `REFACTOR` for Wave 3.

### 4. Parallel dispatch (in a single assistant turn)

Spawn all Wave-N subagents via parallel `Task` calls in one turn. Tim Dietrich's rule: be specific about the count. Print before dispatch:

```
Wave <N>/<total> dispatching <count> agents: <agent-list>
  → waiting for DONE|<path> barriers via SubagentStop hook…
```

Subagents return **only** `DONE|<artifact-path>`. **TaskOutput is forbidden** (barkain rule) — each agent writes to `.claude/phases/<slug>/phase-<NN>-scratchpad/` and returns the path only.

### 5. Wave barrier

`wave-barrier.sh` (SubagentStop) updates `.claude/state/wave.json` and `current-task.json.wave_status`, but only for canonical `DONE|<path>` completions. `BLOCKED|<reason>` removes the agent from `active_agents` without advancing the wave. When the JSON shows `status: "ready-for-next-wave"`, emit:

```
✓ Wave <N> complete: <K>/<expected> artifacts written
```

Then advance to Wave N+1: re-seed state, call `eneo_phase_set`, dispatch.

### 6. Guardrails (Section H)

- **Over-parallelization.** Before dispatching N parallel agents require ≥3 *unrelated* tasks with clean file boundaries. Otherwise run serial.
- **Shared-file race.** Reject a wave where two agents claim overlapping `files:`. Print which files overlap and suggest splitting.

### 7. Interruption recovery

On re-invocation, read `.claude/state/current-task.json` and `.claude/state/wave.json`. If a wave is mid-flight (`status: "in-progress"`) and some agents returned while others did not, print:

```
Resuming <slug> at Phase <N> Wave <K> (<done>/<expected> returned).
Re-dispatching incomplete agents: <list>
```

Re-dispatch only the agents whose artifacts are missing in the scratchpad directory.

### 8. Phase completion

When the final wave of a phase returns, mark the phase file's status `shipped` (set via `eneo_task_update '.phase = $__next'` if more phases remain). Print:

```
✓ Phase <N>/<total> complete. Scratchpad: .claude/phases/<slug>/phase-<NN>-scratchpad/
  Next: /eneo-verify
```

## Every error uses the 3-part structure

Example (phase file missing):

```
✗ Cannot run phase <N>: .claude/phases/<slug>/phase-<NN>-*.md not found.
  Rule: /eneo-start requires an authored phase file produced by /eneo-plan.
  Fix:  run /eneo-plan to populate the phases, then /eneo-start <slug> <N>.
```
