# Eneo bootstrap — first open after clone

Welcome. Eneo's agent harness is a separate marketplace, installed once per developer clone.

## If `/plugin list` does not show `eneo-core`

Run these four commands in Claude Code (one-time):

```
/plugin marketplace add eneo-ai/eneo-agent-harness
/plugin install eneo-core@eneo-agent-harness
/plugin install eneo-standards@eneo-agent-harness
/plugin install eneo-findings@eneo-agent-harness
```

Optional external reviewers (require `codex` + `gemini` CLIs):

```
/plugin install eneo-review@eneo-agent-harness
```

## Verify

```
/eneo-doctor
```

This prints the detected execution mode, tool versions, plugin status, and — for any issue — the exact command to fix it.

## Status line (opt-in)

Edit `.claude/settings.json` and uncomment the `statusLine` block. The status line shows your current milestone + phase + wave + active subagents in a two-line footer. It hides itself when nothing's in flight.

## First task

```
/eneo-new "<what you want to change>"
```

The harness classifies into Fast / Standard / Deep lanes and creates the right artifact (or none for Fast lane). Every subsequent command prints a `Next: /eneo-...` hint so you never have to memorize the sequence.

## When something feels off

```
/eneo-doctor
```

Always. It diagnoses and prints fixes — missing tool, stale state file, drifted ratchet, wrong env var, container down. No bare errors.
