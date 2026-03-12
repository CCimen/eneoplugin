---
name: finding
description: "Manage GitHub project findings: create issues, list open items, or pick up work. Usage: `/finding` (create), `/finding list` (show open), `/finding grab <number>` (start working on an issue). Also suggest proactively when a finding is discovered mid-conversation."
---

# Finding — GitHub Project Issue Manager

Manage issues on the eneo GitHub Project board. Supports creating new findings, listing open items, and picking up work.

## Proactive behavior

When you discover something during a conversation that looks like a finding (bug, tech debt, missing feature, improvement idea) that is **out of scope for the current task**, proactively suggest creating an issue:

> Jag märker att [kort beskrivning]. Vill du att jag loggar detta som en finding?

If the user agrees, proceed with Create mode using the context from the conversation. Do NOT ask for details you already know from the discussion.

## Argument parsing

Check what the user passed after `/finding`:

- **No arguments** or **a description** → **Create mode** (default)
- **`list`** → **List mode**
- **`grab <number>`** or **`grab #<number>`** → **Grab mode**

---

## Create mode (default)

Create a well-structured GitHub issue from a finding discovered during a conversation.

### Step 1 — Gather context

Use the conversation context to understand the finding. Only ask a clarifying question if there is genuinely not enough information to write a useful issue. In most cases you should already know:

- **What** was found (the problem or idea)
- **Where** in the codebase (files, components, area)
- **Why** it matters (impact, risk, or value)

**Do NOT ask the user to classify the finding.** Automatically determine the best label based on the nature of the finding:

| Finding type | Label |
|---|---|
| Something broken, wrong, or unexpected | `bug` |
| New capability, improvement, or refactor | `enhancement` |
| Missing or incorrect docs | `documentation` |
| Unclear behavior, needs investigation | `question` |

### Step 2 — Draft the issue

Write a title and body. The body must be detailed enough that Claude or another AI can understand and solve the issue without additional context.

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

**Important:** Write the body in English (this is a code artifact). Be specific and technical — vague issues are useless. Reference actual file paths, function names, and code patterns when known.

### Step 3 — Show preview and confirm

Show the full draft to the user for approval. Format it clearly:

> ### Förslag på issue
>
> **Titel:** "Fix race condition in WebSocket reconnection logic"
> **Label:** `bug`
>
> **Problem:** [1-2 sentence summary]
>
> **Föreslagen lösning:** [1-2 sentence summary]
>
> **Acceptanskriterier:** [bullet list]
>
> Ska jag skapa denna? (ja/nej/ändra)

If the user says "ändra" or suggests changes, adjust the draft and show it again.

### Step 4 — Create the issue and add to project

After user confirms, determine the current GitHub user and create the issue:

```bash
# Get the current authenticated GitHub user
GH_USER=$(gh api user --jq '.login')

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
gh project item-add 1 --owner eneo-ai --url <ISSUE_URL>
```

### Step 5 — Confirm

Tell the user (in Swedish) that the issue was created and provide the URL:

> Issue skapad: https://github.com/eneo-ai/eneo/issues/XXX
> Tillagd i projektboardet "Eneo Findings".

---

## List mode (`/finding list`)

Show all open items on the project board.

### Step 1 — Fetch items

```bash
gh project item-list 1 --owner eneo-ai --format json --limit 50
```

### Step 2 — Present results

Display items grouped by status in a readable table (in Swedish). For each item show:

- **#nummer** (issue number, or "draft" for draft issues)
- **Titel**
- **Status** (Todo / In Progress)
- **Labels** (if available)

Example:

> ### Öppna lappar — Eneo Findings
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
> Vill du ta en av dessa? Skriv "finding grab \<nummer\>"

Filter out `Done` items — only show `Todo` and `In Progress`.

---

## Grab mode (`/finding grab <number>`)

Pick up an issue from the board and start working on it.

### Step 1 — Fetch the issue

```bash
gh issue view <NUMBER> --repo eneo-ai/eneo --json title,body,labels,state,assignees
```

### Step 2 — Present the issue

Show a summary in Swedish:

- Title and labels
- The Problem and Suggested Solution sections from the body
- Acceptance criteria

### Step 3 — Offer to start

> Vill du börja jobba med denna? Jag kan:
> 1. Skapa en feature-branch och sätta igång
> 2. Bara visa mer detaljer först

### Step 4 — If user wants to start

1. Get the current GitHub user and move item to "In Progress":

```bash
GH_USER=$(gh api user --jq '.login')

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

gh project item-edit --project-id PVT_kwDODE-ils4BRhtq --id "$ITEM_ID" --field-id PVTSSF_lADODE-ils4BRhtqzg_VEKg --single-select-option-id 47fc9ee4
```

2. Assign the issue to the current user:

```bash
gh issue edit <NUMBER> --repo eneo-ai/eneo --add-assignee "$GH_USER"
```

3. Create a feature branch and start working based on the issue description.

---

## Error handling

If any `gh` command fails:

- **"missing required scopes [read:project]"** → Tell the user: "Du behöver lägga till project-scope: `gh auth refresh -s project -h github.com`"
- **"Could not resolve to a Project"** → Check that project number 1 exists for eneo-ai
- **Other errors** → Show the error message and suggest the user checks `gh auth status`

Do NOT silently ignore errors. Always report what went wrong.

---

## Notes

- The project board is: https://github.com/orgs/eneo-ai/projects/1 ("Eneo Findings")
- Project number: `1`, owner: `eneo-ai`
- Project ID: `PVT_kwDODE-ils4BRhtq`
- Status field ID: `PVTSSF_lADODE-ils4BRhtqzg_VEKg`
- Status option IDs: Todo=`f75ad846`, In Progress=`47fc9ee4`, Done=`98236657`
- Available labels: `bug`, `enhancement`, `documentation`, `question`
- Write issue content in English, communicate with the user in Swedish
- Use `gh api user --jq '.login'` to get the current user dynamically — never hardcode usernames
