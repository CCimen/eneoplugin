---
description: Ask an outside peer reviewer (Codex if installed, else fresh-context Claude) to challenge the current diff or task. Plain-language input — the runner infers paths, focus, phase, and skepticism. Manual only; never an auto hook. Distinct from /eneo-verify gate 7 (automatic Borda) and /eneo-commit (commit-time safety).
argument-hint: "[plan|ready|deep|show] [\"question\"]"
allowed-tools:
  - Read
  - Bash(eneo-peer-review)
  - Bash(eneo-peer-review *)
---

Run `eneo-peer-review $ARGUMENTS` and print its output verbatim. The runner is the source of truth — do not embellish, summarise differently, or re-run sub-tools to "verify" what it produced.

## What the runner does

- **No args** → reviews the current diff/task with inferred paths, focus, and skepticism.
- **First positional matches a known mode** (`plan`, `code`, `green`, `ready`, `deep`, `resume`, `show`, `help`) → that mode is applied; remaining text becomes the developer question. `ready` is an alias for `green` (memorable phrasing for "are we ready to ship?"). Only `green` and `ready` gate the exit code; `deep` is advisory-only with stronger skepticism.
- **Otherwise** → all positional text is treated as the question.
- Provider order: `codex` if installed, else fresh-context `claude`, else `SKIPPED|<reason>` plus install hints.
- State and artifacts: `.claude/peer-reviews/<slug>/state.json` + `iter-NNN.md`. `<slug>` comes from `current-task.json`, else the git branch.
- Output: compact summary (REVIEWER, INDEPENDENCE, VERDICT, GREEN_LIGHT, MIN_SCORE, blockers, next hint, artifact path). Add `--full` or run `show` for the full review.
- The runner is honest about reviewer independence — `claude-fresh` is labeled as a fresh same-model session, not external model diversity.

## Behavioral rules for this command

- If the runner prints `SKIPPED|...`, surface that line and the install hint, then stop.
- If `--require-green` is set and the runner exits 2, repeat the gate-failure line in one sentence and stop. Do not retry, do not relax the gate.
- Never invoke the `codex-reviewer` or `gemini-reviewer` subagents from this command — those are reserved for `/eneo-verify` gate 7's machine-aggregation contract.
- Never call `AskUserQuestion`. Never run shell probes after the runner returns.
- Never edit files in response to the review here — the runner is review-only by design.

## Examples (paste these — they all work)

```
/eneo-peer-review
/eneo-peer-review "Is this the right ownership boundary, or am I patching a symptom?"
/eneo-peer-review plan "Should I implement this slice as scoped?"
/eneo-peer-review ready
/eneo-peer-review deep "Challenge architecture, false-positive risk, and TDD coverage."
/eneo-peer-review show
```

Advanced control (the long form is intentionally deprioritised — only reach for it when the inferred behavior is wrong):

```
/eneo-peer-review --reviewer codex --path frontend/apps/web/src/lib/x.ts --focus ux --focus tests --skepticism skeptical "Is ownership right?"
```

## Tuning

All defaults are env-overridable so different teams can tune without forking:

- `ENEO_PEER_REVIEW_CODEX_MODEL` (default empty — inherit Codex CLI default)
- `ENEO_PEER_REVIEW_CODEX_EFFORT` (default empty — inherit Codex CLI default)
- `ENEO_PEER_REVIEW_CLAUDE_MODEL` (default empty — inherit user's session model; avoids the 1M-context billing trap)
- `ENEO_PEER_REVIEW_CLAUDE_EFFORT` (default empty)
- `ENEO_PEER_REVIEW_CLAUDE_TOOLS` (default `Read,Glob,Grep` — add `Bash` for deeper review)
- `ENEO_PEER_REVIEW_REQUIRED_MIN_SCORE` (default `8`)
- `ENEO_PEER_REVIEW_TIMEOUT_SECONDS` (default `600`)
- `ENEO_PEER_REVIEW_DIFF_BYTES`, `ENEO_PEER_REVIEW_CONTEXT_BYTES`, `ENEO_PEER_REVIEW_MAX_INFERRED_PATHS`

Run `eneo-peer-review --help` from a shell for the full flag list.
