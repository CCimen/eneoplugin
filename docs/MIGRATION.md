# Migration

This repo used to ship a larger set of separate plugins. The current shape is simpler:

- `eneo-core`
- `eneo-standards`
- `eneo-findings`
- `eneo-review`

## TL;DR

1. install the four current plugins
2. remove the old ones if you still have them installed
3. copy the Eneo `.claude/` baseline from `docs/eneo-repo-baseline/`
4. run `/eneo-core:eneo-doctor`

## Install the current plugins

```bash
/plugin install eneo-core@eneo-agent-harness
/plugin install eneo-standards@eneo-agent-harness
/plugin install eneo-findings@eneo-agent-harness
/plugin install eneo-review@eneo-agent-harness   # optional
```

## Remove the old ones

If you still have legacy plugins installed from `eneoplugin`, uninstall them:

```bash
/plugin uninstall karpathy-guidelines@eneoplugin
/plugin uninstall vikunja-kanban@eneoplugin
/plugin uninstall checker@eneoplugin
/plugin uninstall finding@eneoplugin
/plugin uninstall codex-review@eneoplugin
/plugin uninstall gemini-review@eneoplugin
/plugin uninstall frontend-design@eneoplugin
```

## Copy the Eneo baseline

Use the templates under `docs/eneo-repo-baseline/` for:

- `CLAUDE.md`
- `settings.json`
- rule files under `rules/`
- `bootstrap.md`
- `config/findings.json`

## Verify

Run:

```bash
/eneo-core:eneo-doctor
```

If the environment is clean, start work with:

```bash
/eneo-core:eneo-new "<description of the change>"
```

## Notes

- `.claude/` is often ignored wholesale during local rollout. That is fine while you are still testing the harness locally.
- When the app repo is ready for a committed shared baseline, switch from a blanket `.claude/` ignore to selective ignores for runtime-only paths.
- Claude Code's built-in `/recap` is session scope. `/eneo-recap` is milestone scope.
