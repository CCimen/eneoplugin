---
description: Extract a candidate skill from the current session transcript into a draft SKILL.md + ≥3-query eval.md. Requires the developer to author or confirm the eval file before the skill can be merged. Dispatches the learning-extractor subagent in fresh context.
argument-hint: "<short-name-for-the-skill>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
  - Bash(git checkout *)
  - Bash(git add *)
  - Bash(git commit *)
model: opus
---

# /finding-teach

Harvest a repeatable pattern from the current session into a new skill under `plugins/eneo-findings/skills/<name>/`. Section G of the playbook — "The common mechanism is git."

## Pre-flight

- `$ARGUMENTS` is the kebab-case name for the candidate skill. If missing, ask the developer for one via `AskUserQuestion`. Otherwise do the obvious thing.
- Reject names that already exist under `plugins/eneo-findings/skills/`. Print the existing skill path + suggest a different name.

## Steps

### 1. Read the transcript

Gather the session's transcript (via `session_id`) and any open scratchpads under `.claude/phases/<current-slug>/`. This is the input to the learning-extractor.

### 2. Dispatch learning-extractor (fresh context)

```
Task(
  subagent_type: learning-extractor,
  prompt: "Extract a candidate skill named <arg>. Inputs: transcript, scratchpad. Return CANDIDATE|<SKILL.md-path>|<evals.md-path>|<summary>."
)
```

The learning-extractor writes the draft files directly. Section G: "pushy" description, 200–400 line body.

### 3. Require the eval file

After the extractor returns, verify `plugins/eneo-findings/skills/<name>/evals.md` exists AND contains ≥3 queries in the format:

```markdown
## Should trigger

1. <realistic user query>
2. <realistic user query>

## Should not trigger (near-miss)

1. <adjacent-domain query>
```

If fewer than 3 queries or none labeled near-miss, print:

```
✗ evals.md is incomplete.
  Rule: every new skill needs ≥3 eval queries (≥2 should-trigger + ≥1 near-miss) so we can
        measure triggering accuracy (Anthropic's 20-query methodology, scaled down).
  Fix:  add the missing queries to plugins/eneo-findings/skills/<name>/evals.md and re-run
        /finding-teach <name>.
```

and exit.

### 4. Branch and commit

Create a branch in the harness repo and commit the new skill:

```bash
BRANCH="finding-teach/<name>"
git checkout -b "$BRANCH"
git add plugins/eneo-findings/skills/<name>/
git commit -m "Add candidate skill: <name>

Extracted via /finding-teach from session <session-id-short>.
Authors must add the eval file per skill-creator guidance before merging."
```

Do **not** push. The developer opens a PR via `/eneo-ship` or directly via `gh pr create`.

### 5. Final output

```
✓ Candidate skill drafted at plugins/eneo-findings/skills/<name>/
  Eval:     plugins/eneo-findings/skills/<name>/evals.md (<N> queries)
  Branch:   finding-teach/<name> (not pushed)
  Next:     review the SKILL.md + evals, then /eneo-ship or `gh pr create` to merge into the harness.
```

## Why the eval requirement

Anthropic's skills guidance is explicit: skills without evals drift over time. The 20-query methodology measures triggering accuracy; our scaled-down ≥3 (2 should-trigger + 1 near-miss) is the minimum bar to prevent over-triggering. The `skill-creator` plugin (installed in the marketplace) runs a full optimization loop when the developer wants to tighten the description later; `/finding-teach` only guarantees the candidate is well-formed.
