# eneo-agent-harness

Claude Code marketplace for the Eneo workflow.

## TL;DR

- install `eneo-core` and `eneo-standards`
- start work with `/eneo-core:eneo-new "<change>"`
- commit through `/eneo-core:eneo-commit "<message>"`
- run `/eneo-core:eneo-doctor` when the environment feels wrong
- let `eneo-standards` enforce TDD, audit, tenancy, and quality gates

## What this gives developers

- one shared command flow for small and large changes
- deterministic diagnostics instead of ad hoc shell digging
- fast-lane work that stays light
- stronger checks only when the risk justifies them

## The four active plugins

| Plugin | Purpose |
|---|---|
| [`eneo-core`](plugins/eneo-core/) | Main `/eneo-*` workflow, subagents, and implementation skills |
| [`eneo-standards`](plugins/eneo-standards/) | Hooks, validators, helper binaries, and status line |
| [`eneo-findings`](plugins/eneo-findings/) | Findings workflow and learning extraction |
| [`eneo-review`](plugins/eneo-review/) | Trigger-gated external review agents |

## Install

```bash
/plugin marketplace add CCimen/eneoplugin
/plugin install eneo-core@eneoplugin
/plugin install eneo-standards@eneoplugin
/plugin install eneo-findings@eneoplugin
/plugin install eneo-review@eneoplugin   # optional
/reload-plugins
```

Then run:

```bash
/eneo-core:eneo-doctor
```

## Day-to-day flow

- **Fast:** `/eneo-new` → edit → `/eneo-verify` → `/eneo-commit` → `/eneo-ship`
- **Standard:** `/eneo-new` → `/eneo-start` → `/eneo-verify` → `/eneo-commit` → `/eneo-ship`
- **Deep:** `/eneo-new` → `/eneo-discuss` → `/eneo-plan` → `/eneo-start` → `/eneo-verify` → `/eneo-commit` → `/eneo-ship` → `/eneo-recap`

Command discovery note: `/help` mostly shows built-ins. For plugin commands, type `/` and filter by `eneo`, or inspect the plugin in `/plugin`.

## Under the hood

The harness is intentionally split:

- `eneo-core` owns workflow and subagents
- `eneo-standards` owns runtime enforcement
- `eneo-findings` owns backlog capture outside the current task
- `eneo-review` stays quiet until `/eneo-verify` decides a change is risky enough to justify extra review

## Why this does not adopt beads / `br`

The harness already has:

- live flow state in `.claude/state/current-task.json`
- authored artifacts in `.claude/phases/` and `.claude/recaps/`
- GitHub issues / findings for shared backlog work

Adding beads/`br` to the core flow would introduce another state system to reconcile. If the team later wants it, it should be an optional companion workflow, not a required harness dependency.

## Read next

- [docs/MIGRATION.md](docs/MIGRATION.md)
- [docs/STATE_SCHEMA.md](docs/STATE_SCHEMA.md)
- [docs/eneo-repo-baseline/](docs/eneo-repo-baseline/)
- [eneo-harness-playbook.md](eneo-harness-playbook.md)

## License

MIT
