---
name: finding
description: Manage GitHub project findings — create issues, list open items, or pick up work. Usage: `/finding` (create from the current conversation), `/finding list` (show open), `/finding grab <number>` (assign yourself + move to "In Progress"). Also triggers proactively when a finding is discovered mid-conversation that is out of scope for the current task. All board/label/language details are read from `.claude/config/findings.json` so municipalities can override without forking this plugin.
---

# finding — GitHub Project Issue Manager

Manage issues on the current project's findings board. Supports creating new findings, listing open items, and picking up work. All municipality-specific IDs live in `.claude/config/findings.json` — never hardcoded here.

## Configuration contract

Read `.claude/config/findings.json` at the start of every invocation. Expected schema:

```json
{
  "github_repo": "eneo-ai/eneo",
  "project_owner": "eneo-ai",
  "project_number": 1,
  "project_id": "PVT_kwDODE-ils4BRhtq",
  "status_field_id": "PVTSSF_lADODE-ils4BRhtqzg_VEKg",
  "status_options": {
    "todo": "f75ad846",
    "in_progress": "47fc9ee4",
    "done": "98236657"
  },
  "labels": ["bug", "enhancement", "documentation", "question"],
  "language": "sv",
  "board_name": "Eneo Findings"
}
```

If the file is missing, print:

```
✗ .claude/config/findings.json not found.
  Rule: the finding plugin reads all board/label settings from this file so
        municipalities can override without editing plugin code.
  Fix:  copy the template from docs/eneo-repo-baseline/config/findings.json into
        .claude/config/findings.json and fill in your project/IDs.
```

and exit.

Every `gh` invocation below uses **variables** read from this config — no literal project numbers or UUIDs in this file.

## Proactive behavior

When you discover something during a conversation that looks like a finding (bug, tech debt, missing feature, improvement idea) that is **out of scope for the current task**, proactively suggest creating an issue. Phrase the suggestion in the configured `language` (default Swedish):

> Jag märker att [kort beskrivning]. Vill du att jag loggar detta som en finding?

If the user agrees, proceed with Create mode using the context from the conversation. Do NOT ask for details you already know from the discussion.

## Argument parsing

Check what the user passed after `/finding`:

- **No arguments** or **a description** → **Create mode** (default)
- **`list`** → **List mode**
- **`grab <number>`** or **`grab #<number>`** → **Grab mode**

## Create mode (default)

Create a well-structured GitHub issue from a finding discovered during a conversation.

### Step 1 — Gather context

Use the conversation context to understand the finding. Only ask a clarifying question if there is genuinely not enough information to write a useful issue. In most cases you should already know:

- **What** was found (the problem or idea)
- **Where** in the codebase (files, components, area)
- **Why** it matters (impact, risk, or value)

**Do NOT ask the user to classify the finding.** Auto-classify by nature:

| Finding type | Label |
|---|---|
| Something broken, wrong, or unexpected | `bug` |
| New capability, improvement, or refactor | `enhancement` |
| Missing or incorrect docs | `documentation` |
| Unclear behavior, needs investigation | `question` |

Only use labels from `config.labels` — if your classification needs a label not in the list, fall back to the closest available and note it in the body.

### Step 2 — Draft the issue

Write a title and body. The body must be detailed enough that Claude or another AI can understand and solve the issue without additional context.

**Title:** short, specific, action-oriented.

**Body template:**

```markdown
## Problem

[Clear description of what's wrong or what's missing.]

## Context

- **Area:** [Which part of the codebase]
- **Discovered while:** [Brief note on what work led to this discovery]
- **Related files:** [List specific files if known]

## Steps to Reproduce (if applicable)

1. [Step 1]
2. [Expected vs actual result]

## Suggested Solution

[Concrete suggestion. Include specific files, approach, gotchas.]

## Acceptance Criteria

- [ ] [What "done" looks like — testable, specific]
```

Write the body in **English** (code artifact); communicate with the user in the configured `language`.

### Step 3 — Show preview and confirm

Show the full draft to the user in the configured language. Format clearly with title, label, problem summary, suggested solution summary, acceptance criteria, and a confirmation prompt.

If the user requests changes, adjust the draft and show it again.

### Step 4 — Create the issue and add to project

After confirmation:

```bash
# Load config
GITHUB_REPO=$(jq -r '.github_repo' .claude/config/findings.json)
PROJECT_OWNER=$(jq -r '.project_owner' .claude/config/findings.json)
PROJECT_NUMBER=$(jq -r '.project_number' .claude/config/findings.json)

# Create the issue (heredoc for body)
ISSUE_URL=$(gh issue create \
  --repo "$GITHUB_REPO" \
  --title "<TITLE>" \
  --label "<LABEL>" \
  --body "$(cat <<'ISSUE_EOF'
<BODY>
ISSUE_EOF
)")

# Add to project board
gh project item-add "$PROJECT_NUMBER" --owner "$PROJECT_OWNER" --url "$ISSUE_URL"
```

### Step 5 — Confirm to the user

Report in the configured `language` with the URL and a note that the item was added to the board (use `board_name` from config).

## List mode (`/finding list`)

```bash
PROJECT_NUMBER=$(jq -r '.project_number' .claude/config/findings.json)
PROJECT_OWNER=$(jq -r '.project_owner' .claude/config/findings.json)

gh project item-list "$PROJECT_NUMBER" --owner "$PROJECT_OWNER" --format json --limit 50
```

Group items by status (filter out `Done`). Display a readable table in the configured `language` with issue number, title, and labels.

## Grab mode (`/finding grab <number>`)

Pick up an issue from the board and start working on it.

### Step 1 — Fetch the issue

```bash
GITHUB_REPO=$(jq -r '.github_repo' .claude/config/findings.json)
gh issue view <NUMBER> --repo "$GITHUB_REPO" --json title,body,labels,state,assignees
```

### Step 2 — Present summary

Show title, labels, Problem + Suggested Solution, acceptance criteria (in the configured language).

### Step 3 — Offer to start

Ask: create a feature branch and start, or show more details?

### Step 4 — If starting

Move the item to "In Progress" and assign the current user:

```bash
GH_USER=$(gh api user --jq '.login')
PROJECT_OWNER=$(jq -r '.project_owner' .claude/config/findings.json)
PROJECT_NUMBER=$(jq -r '.project_number' .claude/config/findings.json)
PROJECT_ID=$(jq -r '.project_id' .claude/config/findings.json)
STATUS_FIELD_ID=$(jq -r '.status_field_id' .claude/config/findings.json)
IN_PROGRESS_OPT=$(jq -r '.status_options.in_progress' .claude/config/findings.json)
GITHUB_REPO=$(jq -r '.github_repo' .claude/config/findings.json)

# Resolve the project item id for this issue
ITEM_ID=$(gh project item-list "$PROJECT_NUMBER" --owner "$PROJECT_OWNER" --format json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data.get('items', []):
    content = item.get('content', {})
    if content.get('number') == <NUMBER>:
        print(item['id'])
        break
")

gh project item-edit \
  --project-id "$PROJECT_ID" \
  --id "$ITEM_ID" \
  --field-id "$STATUS_FIELD_ID" \
  --single-select-option-id "$IN_PROGRESS_OPT"

gh issue edit <NUMBER> --repo "$GITHUB_REPO" --add-assignee "$GH_USER"
```

Create a feature branch and start working based on the issue description.

## Error handling

Every `gh` failure gets a three-part fix-oriented error:

- `missing required scopes [read:project]`
  - Rule: `gh` needs the `project` scope to read the board.
  - Fix:  `gh auth refresh -s project -h github.com`
- `Could not resolve to a Project`
  - Rule: `.claude/config/findings.json` `project_number` must exist for `project_owner`.
  - Fix:  verify the values; run `gh project list --owner <owner>` to confirm.
- Other errors — show the raw error and suggest `gh auth status`.

## Notes

- All values (project id, status IDs, labels, language, board name) live in `.claude/config/findings.json`. Any other municipality forks the config, not the skill.
- Write issue body in English; communicate with the user in the configured language (Swedish by default).
- Use `gh api user --jq '.login'` to get the current user dynamically — never hardcode.
