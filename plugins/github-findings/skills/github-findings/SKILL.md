---
name: github-findings
description: "Manage GitHub project findings: create issues, list open items, or pick up work. Usage: `/github-findings` (create), `/github-findings list` (show open), `/github-findings grab <number>` (start working on an issue)."
---

# Finding — GitHub Project Issue Manager

Manage issues on the eneo GitHub Project board. Supports creating new findings, listing open items, and picking up work.

## Argument parsing

Check what the user passed after `/finding`:

- **No arguments** or **a description** → **Create mode** (default)
- **`list`** → **List mode**
- **`grab <number>`** or **`grab #<number>`** → **Grab mode**

---

## Create mode (default)

Create a well-structured GitHub issue from a finding discovered during a conversation.

### When to use

- A bug or unexpected behavior is discovered while working on something else
- An improvement idea comes up that's out of scope for the current task
- Technical debt or a code smell is noticed
- A missing feature or gap is identified

### Step 1 — Gather context

If the user invoked `/finding` without arguments or with a brief note, ask a short clarifying question to understand:

1. **What** was found (the problem or idea)
2. **Where** in the codebase (files, components, area)
3. **Why** it matters (impact, risk, or value)
4. **Label** — one of: `bug`, `enhancement`, `documentation` (default: `bug`)

If the conversation already provides enough context (e.g. we just discussed the issue in detail), skip the question and proceed directly. Use your judgment — don't ask for things you already know.

### Step 2 — Draft the issue

Write a title and body using this template. The body must be detailed enough that Claude or another AI can understand and solve the issue without additional context.

**Title format:** Short, specific, action-oriented (e.g. "Fix race condition in WebSocket reconnection logic")

**Body template:**

```markdown
## Problem

[Clear description of what's wrong or what's missing. Include error messages, unexpected behavior, or the gap.]

## Context

- **Area:** [Which part of the codebase — e.g. backend/src/intric/jobs/, frontend/src/lib/components/]
- **Discovered while:** [Brief note on what work led to this discovery]
- **Related files:** [List specific files if known]

## Steps to Reproduce (if applicable)

1. [Step 1]
2. [Step 2]
3. [Expected vs actual result]

## Suggested Solution

[Concrete suggestion for how to fix/implement this. Include specific files to change, approach to take, and any gotchas. This section is critical — it should give enough direction for an AI agent to start working on it.]

## Acceptance Criteria

- [ ] [What "done" looks like — testable, specific]
- [ ] [Additional criteria if needed]
```

**Important:** Write the body in English (this is a code artifact). Be specific and technical — vague issues are useless. Reference actual file paths, function names, and code patterns.

### Step 3 — Confirm with user

Show the drafted title and a brief summary of the body to the user. Ask for confirmation before creating. Example:

> **Issue:** "Fix race condition in WebSocket reconnection logic"
> **Label:** bug
> **Ska jag skapa denna?**

### Step 4 — Create the issue and add to project

After user confirms, run these commands:

```bash
# Ensure correct GitHub account
gh auth switch --user MaxErikssonDevize 2>/dev/null

# Create the issue (use heredoc for body)
gh issue create \
  --repo eneo-ai/eneo \
  --title "<TITLE>" \
  --label "<LABEL>" \
  --body "$(cat <<'ISSUE_EOF'
<BODY>
ISSUE_EOF
)"
```

Then add it to the project board:

```bash
# Get the issue URL from the create output, then add to project
gh project item-add 1 --owner eneo-ai --url <ISSUE_URL>
```

### Step 5 — Confirm

Tell the user (in Swedish) that the issue was created and provide the URL. Example:

> Issue skapad: https://github.com/eneo-ai/eneo/issues/XXX
> Tillagd i projektboardet.

---

## List mode (`/finding list`)

Show all open items on the project board so the user can see what's available.

### Step 1 — Fetch items

```bash
gh auth switch --user MaxErikssonDevize 2>/dev/null

# List all Todo and In Progress items from the project
gh project item-list 1 --owner eneo-ai --format json --limit 50
```

### Step 2 — Present results

Display the items grouped by status in a readable table format (in Swedish). For each item show:

- **#nummer** (issue number, or "draft" for draft issues)
- **Titel**
- **Status** (Todo / In Progress)
- **Labels** (if available)

Example output:

> ### Öppna lappar på projektboardet
>
> **Todo:**
> | # | Titel | Labels |
> |---|-------|--------|
> | #264 | Fix auth token refresh | bug |
> | #265 | Add pagination to admin list | enhancement |
>
> **In Progress:**
> | # | Titel | Labels |
> |---|-------|--------|
> | #260 | WebSocket reconnection | bug |
>
> Vill du ta en av dessa? Skriv `/finding grab <nummer>`

Filter out `Done` items — only show `Todo` and `In Progress`.

---

## Grab mode (`/finding grab <number>`)

Pick up an issue from the board and start working on it.

### Step 1 — Fetch the issue

```bash
gh auth switch --user MaxErikssonDevize 2>/dev/null

# Read the issue details
gh issue view <NUMBER> --repo eneo-ai/eneo --json title,body,labels,state,assignees
```

### Step 2 — Present the issue

Show the user a summary of the issue in Swedish, including:

- Title and labels
- The Problem and Suggested Solution sections from the body
- Any acceptance criteria

### Step 3 — Offer to start

Ask the user:

> Vill du börja jobba med denna? Jag kan:
> 1. Skapa en feature-branch och sätta igång
> 2. Bara visa mer detaljer först

### Step 4 — If user wants to start

1. Move the item to "In Progress" on the project board:

```bash
# Get the project item ID for this issue
ITEM_ID=$(gh project item-list 1 --owner eneo-ai --format json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data.get('items', []):
    content = item.get('content', {})
    if content.get('number') == <NUMBER>:
        print(item['id'])
        break
")

# Get the Status field ID and the 'In Progress' option ID
gh project item-edit --project-id PVT_kwDODE-ils4BRhtq --id "$ITEM_ID" --field-id PVTSSF_lADODE-ils4BRhtqzg_VEKg --single-select-option-id 47fc9ee4
```

2. Assign the issue:

```bash
gh issue edit <NUMBER> --repo eneo-ai/eneo --add-assignee MaxErikssonDevize
```

3. Create a feature branch and start working based on the issue description.

---

## Notes

- Always use `gh auth switch --user MaxErikssonDevize` before gh operations
- The project board is: https://github.com/orgs/eneo-ai/projects/1
- Project number: `1`, owner: `eneo-ai`
- Project ID: `PVT_kwDODE-ils4BRhtq`
- Status field ID: `PVTSSF_lADODE-ils4BRhtqzg_VEKg`
- Status option IDs: Todo=`f75ad846`, In Progress=`47fc9ee4`, Done=`98236657`
- Available labels: `bug`, `enhancement`, `documentation`, `question`
- Write issue content in English, communicate with the user in Swedish
