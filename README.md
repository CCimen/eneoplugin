# eneo-agent-harness

A Claude Code plugin marketplace that turns the Eneo codebase into a **hook-enforced, wave-executed, ratchet-gated** development harness for the core team and external kommun contributors.

> **Heads up:** this marketplace was previously shipped as seven separate plugins under the name `eneoplugin`. It has been consolidated into **four** plugins with a `/eneo-*` slash-command lineup, a shared dual-mode devcontainer library, a status-line integration, and a conditional external-review tournament. See [`docs/MIGRATION.md`](docs/MIGRATION.md) if you're upgrading from v1.

## Design spec

Everything in this repo implements the playbook at [`eneo-harness-playbook.md`](eneo-harness-playbook.md). If a detail here contradicts the playbook, the playbook wins.

## The four plugins

| Plugin | Purpose |
|---|---|
| [`eneo-core`](plugins/eneo-core/) | 9 `/eneo-*` slash commands, 10 subagents (TDD pair, domain specialists, reviewers, learning extractor, autoreason judge), 8 skills (PRD template, prd-to-plan, prd-to-issues, FastAPI / Pydantic v2 / SvelteKit / audit-log-writer, frontend-design). |
| [`eneo-standards`](plugins/eneo-standards/) | Hook-enforced standards: TDD phase gate, bash firewall, wave barrier, ratchet enforcement, protected files, shared `env.sh` dual-mode library, ported pyright typecheck, 5 Python validators, opt-in two-line status line. |
| [`eneo-review`](plugins/eneo-review/) | Two trigger-gated external reviewer subagents (Codex + Gemini). Invoked only by `/eneo-verify` on risky changes (`audit:schema`, `tenancy:cross`, `authz`, LOC > 800). Output feeds the autoreason A/B/AB tournament. |
| [`eneo-findings`](plugins/eneo-findings/) | `/finding` skill for GitHub Project findings (read config from `.claude/config/findings.json`) + `/finding-teach` command to extract a session learning into a candidate skill. |

## Install

From any Eneo clone with the marketplace configured:

```
/plugin marketplace add eneo-ai/eneo-agent-harness
/plugin install eneo-core@eneo-agent-harness
/plugin install eneo-standards@eneo-agent-harness
/plugin install eneo-findings@eneo-agent-harness
/plugin install eneo-review@eneo-agent-harness   # optional
```

Then verify the environment:

```
/eneo-doctor
```

## Command lineup

```
/eneo-new <description>         → triage + create artifact (Fast/Standard/Deep lane)
/eneo-discuss                    → Socratic interview + 90/70 confidence gate (Deep)
/eneo-plan                       → PRD → tracer-bullet phased plan (Deep)
/eneo-start [<slug>] [<phase>    → resume work + Wave → Checkpoint → Wave orchestration
           | --phase <state>]       (the emergency phase override lives here)
/eneo-verify                     → 7-gate ratchet + conditional adversarial review
/eneo-ship                       → gh pr create with enforced tenancy/audit/PRD/phase metadata
/eneo-recap                      → close milestone, write milestone recap, archive phases
/eneo-doctor                     → actionable diagnostics (runnable any time)
/eneo-prune                      → quarterly skill + recap cleanup
/finding-teach <name>            → extract a session pattern into a candidate skill
```

Command discovery note: `/help` in Claude Code primarily shows built-in commands. For plugin commands, type `/` and then filter by `eneo` (or open `/plugin`). This is expected Claude behavior, not a harness bug.

Three lanes, three happy paths:

- **Fast:** `/eneo-new` (choose "proceed") → edit → `/eneo-verify` → `/eneo-ship`
- **Standard:** `/eneo-new` → `/eneo-start` → `/eneo-verify` → `/eneo-ship`
- **Deep:** `/eneo-new` → `/eneo-discuss` → `/eneo-plan` → `/eneo-start` (per phase) → `/eneo-verify` → `/eneo-ship` → `/eneo-recap`

Every successful command prints a `Next: /eneo-<verb>` hint inferred from state. Every error is three-part: **what / rule / fix**.

## Dual-mode devcontainer

Hooks auto-detect where tools live — inside the devcontainer, on the host with docker-exec routing, or native. Override with `ENEO_DEVCONTAINER_MODE` (`in-container` | `host-with-docker` | `native` | `disabled`). `/eneo-doctor` prints the detected mode and the right env var to set for any override.

All hook examples in the playbook wrap commands in `eneo_exec` from [`plugins/eneo-standards/hooks/lib/env.sh`](plugins/eneo-standards/hooks/lib/env.sh) so the same script works on a host laptop and inside the devcontainer.

## Status line (opt-in)

Add to your `.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "${CLAUDE_PLUGIN_ROOT}/statusline/eneo-statusline.sh"
  }
}
```

Renders a two-line footer: session context (model/session, worktree, branch, dirty counts, ctx%, high-water rate-limit usage, duration) + harness state (`<slug> · Phase 2/3 · Wave 2/3 [▓▓▓░░] · GREEN · 🔨 active-agents`). Cost is hidden by default; set `ENEO_STATUSLINE_SHOW_COST=1` if you want it back. Hides line 2 automatically when no milestone is in flight. Test with:

```sh
echo '{"model":{"display_name":"Opus 4.7"},"workspace":{"current_dir":"/eneo"},"context_window":{"used_percentage":42},"cost":{"total_cost_usd":0.18,"total_duration_ms":720000},"session_id":"test"}' \
  | plugins/eneo-standards/statusline/eneo-statusline.sh
```

## State schema (the DX source of truth)

`.claude/state/current-task.json` is the single state file that every hook, every command, `/eneo-doctor`, and the status line read and write. The shape is documented in [`docs/STATE_SCHEMA.md`](docs/STATE_SCHEMA.md), and every writer goes through the `eneo_task_update` helper in `plugins/eneo-standards/hooks/lib/state.sh` so schema drift is architecturally prevented.

## Eneo repo baseline

New Eneo clones need a small `.claude/` baseline (CLAUDE.md, rules files, settings.json, bootstrap.md, config/findings.json). Templates live at [`docs/eneo-repo-baseline/`](docs/eneo-repo-baseline/); see [`docs/MIGRATION.md`](docs/MIGRATION.md) for the copy-in steps.

The baseline settings template now includes a starter `permissions.allow` list for common safe harness commands. After your first few sessions, run `/fewer-permission-prompts` to tune the allowlist based on real usage instead of guesswork.

During local adoption, many Eneo clones still ignore `.claude/` wholesale. That is fine for experimentation because it keeps runtime files like `.claude/state/` and `.claude/stats/` out of Git. When you're ready to commit a shared baseline, replace the blanket ignore with selective ignores for runtime-only paths instead of changing it ad hoc mid-rollout.

## Built-in recaps vs milestone recaps

Claude Code now has a built-in `/recap` session summary feature. Keep that enabled for "what just happened in this session?" and use `/eneo-recap` for the harness-level milestone closeout that writes `.claude/recaps/<slug>.md`, closes the PRD issue, and archives phase artifacts. They solve different problems and should coexist.

## Why this harness does not adopt beads / `br`

For now, this harness intentionally avoids adding a third issue-tracking layer such as beads/`br` into the core workflow. The current stack already has:

- runtime flow state in `.claude/state/current-task.json`
- phase and recap artifacts under `.claude/`
- GitHub issues / findings for shared backlog and review work

Adding `br` as a required dependency would create overlapping sources of truth and make Fast-lane work heavier. If the team later wants a local-first backlog manager, `br` can be documented as an optional companion workflow, but it is not part of the core `/eneo-*` flow.

## Post-clone chmod

Some clone flows strip executable bits. After installing, run once:

```sh
chmod +x plugins/eneo-standards/hooks/*.sh \
         plugins/eneo-standards/hooks/*.py \
         plugins/eneo-standards/hooks/validators/*.py \
         plugins/eneo-standards/bin/* \
         plugins/eneo-standards/hooks/lib/env.sh \
         plugins/eneo-standards/statusline/eneo-statusline.sh
```

Then `/eneo-doctor` will confirm everything is wired.

## Future private overlay

The architecture preserves a stackable-marketplace seam for a future municipality-specific overlay (`eneo-ai/eneo-agent-harness-private`). v1 ships none, but every design decision keeps the door open at zero rework cost. Details: [`docs/FUTURE_PRIVATE_OVERLAY.md`](docs/FUTURE_PRIVATE_OVERLAY.md).

## Key docs

- [`eneo-harness-playbook.md`](eneo-harness-playbook.md) — design spec; the source of truth.
- [`docs/MIGRATION.md`](docs/MIGRATION.md) — upgrading from v1.
- [`docs/STATE_SCHEMA.md`](docs/STATE_SCHEMA.md) — `.claude/state/current-task.json` shape + write contract.
- [`docs/FUTURE_PRIVATE_OVERLAY.md`](docs/FUTURE_PRIVATE_OVERLAY.md) — the overlay-ready architecture.
- [`docs/eneo-repo-baseline/`](docs/eneo-repo-baseline/) — templates to copy into each Eneo clone's `.claude/`.
- [`docs/superpowers/plans/2026-04-16-eneo-harness-migration.md`](docs/superpowers/plans/) — the phased implementation plan this repo shipped.

## License

MIT
