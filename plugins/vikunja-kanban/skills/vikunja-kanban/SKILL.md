---
name: vikunja-kanban
description: Create and update Vikunja Kanban cards with safe, high-level Swedish progress updates (English technical terms preserved). Use when creating a new feature card, linking a PR to an existing card, or posting progress updates for Vikunja tasks.
---

# Vikunja Kanban Skill

Create and update Vikunja Kanban cards safely for the **Internal TODO** project. This skill is designed to avoid accidental data loss:

- Never delete tasks
- Only edit descriptions for tasks marked as managed by this skill
- Default to comment-only updates for existing tasks

## Required setup

Set environment variables (do not commit these):

- `VIKUNJA_BASE_URL` (server root, **no** `/api/v1` suffix)
- `VIKUNJA_API_TOKEN` (API token)
- Optional: `VIKUNJA_PROJECT_NAME` (default: `Internal TODO`)
- Optional: `VIKUNJA_VIEW_NAME` (default: `Kanban`)

**Finding the API token:** in the Vikunja web UI, open your user settings and create an API token.

## Commands

All commands use the helper script located at `scripts/vikunja.py` (relative to this `SKILL.md`).

### 1) Ensure a task exists

Creates a task if it doesn’t exist, or returns the existing one:

```bash
python3 scripts/vikunja.py ensure-task
  --title "Audit logging"
  --goal "Skapa audit logging i admin"
  --requirements "Logga viktiga actions, export via UI"
  --solution "Server-side audit events + UI listing"
  --definition "Audit events syns i Admin, export fungerar"
  --pr-number 84
  --pr-url "https://..."
```

Matching logic:
1. `--task-id` if provided
2. Label `pr-<num>`
3. Title prefix `[PR-<num>]`
4. Branch marker `[branch:<name>]`
5. Exact title match (when no PR data is provided)

If no match is found, the task is created in the **Idé** column with a managed marker:
`<!-- vikunja-skill:managed -->`



### 1b) Ensure a task with labels

```bash
python3 scripts/vikunja.py ensure-task
  --title "Audit logging"
  --labels "security,audit"
```


### 2) Progress update

Adds a Swedish high-level status comment and updates `percent_done`:

```bash
python3 scripts/vikunja.py progress-update
  --pr-number 84
  --done 5
  --total 10
  --summary "Vi har implementerat core logging och UI"
  --completed "API events + Admin list"
  --in-progress "Export + filtering"
  --next "Koppla till org-roller"
  --blockers "Inga"
```

If the task is managed (marker present), a small **Status** block in the description is updated. Otherwise, only a comment is added.

### 3) Link PR to a task

```bash
python3 scripts/vikunja.py link-pr
  --task-id 84
  --pr-number 84
  --pr-url "https://..."
```

Adds label `pr-84` and a short comment with the PR URL. No description edits unless the managed marker exists.



### 3b) Manage labels on a task

```bash
python3 scripts/vikunja.py labels
  --task-id 84
  --add "security,audit"

python3 scripts/vikunja.py labels
  --task-id 84
  --remove "legacy"

python3 scripts/vikunja.py labels
  --task-id 84
  --replace "security,high"
```


### 4) Move a task (optional)

```bash
python3 scripts/vikunja.py move-task
  --task-id 84
  --to "Under verifiering"
```

Moves the task to the named Kanban bucket. No content edits.

## Templates and references

- `assets/task_description_template.md` — Swedish task template
- `assets/progress_comment_template.md` — Swedish progress update template
- `references/vikunja-api.md` — endpoint overview used by this skill

## Output style

Write progress in Swedish at a high level for project leaders; keep technical terms in English (e.g., “audit”, “PR”, “API”).
