---
description: Manage findings on the GitHub project board — create from the current conversation, list open items, or grab an issue to start working on it. Subcommands — `/finding` (create), `/finding list` (show open), `/finding grab <number>` (assign + set In Progress + branch). Reads board IDs from `.claude/config/findings.json`.
argument-hint: "[list | grab <number> | <free-text description>]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(gh *)
  - Bash(git checkout *)
  - Bash(jq *)
  - Bash(python3 *)
model: sonnet
---

# /finding

Thin slash-command wrapper that dispatches to the `finding` skill in this same plugin. The skill (`plugins/eneo-findings/skills/finding/SKILL.md`) owns every step; this command exists so the behavior is invokable without typing the skill name.

## What it does (one-liner)

Reads `$ARGUMENTS` and hands off to the skill:

- `list` → List mode.
- `grab <number>` or `grab #<number>` → Grab mode (move item to "In Progress", assign current user, create a feature branch).
- anything else (or empty) → Create mode (write a structured issue from the current conversation).

Refer to the skill for the full step-by-step, including config-file contract (`.claude/config/findings.json`), issue-body template, and error-handling conventions.

## DX contract

- **Sensible defaults, sparse prompts.** Only use `AskUserQuestion` when the developer's intent is genuinely ambiguous — e.g., they typed `/finding grab` with no number.
- **Every run ends with a `Next:` hint** (the skill handles this — Create mode ends with the issue URL + "hämta den med `/finding grab <N>`" style hint in the configured language).
- **3-part errors.** Every `gh` failure prints `what / rule / fix` — the skill already implements this.

## Why a command + a skill instead of just a skill

Slash-command surface makes the three modes discoverable via `/plugin list` and tab-completion. The skill keeps the heavy lifting testable and referenceable from `/finding-teach` documentation. Keeping the command thin prevents drift — there is one source of truth in the SKILL.md.
