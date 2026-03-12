# eneoplugin

A Claude Code plugin marketplace with AI team behavioral guidelines for Eneo developers.

## Installation

### 1. Add the marketplace

```
/plugin marketplace add CCimen/eneoplugin
```

### 2. Install plugins

```
/plugin install karpathy-guidelines@eneoplugin
/plugin install frontend-design@eneoplugin
/plugin install checker@eneoplugin
/plugin install vikunja-kanban@eneoplugin
/plugin install github-findings@eneoplugin
```

## Available Plugins

### karpathy-guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Includes:

- **CLAUDE.md** - Automatically loaded guidelines emphasizing:
  1. Think Before Coding
  2. Simplicity First
  3. Surgical Changes
  4. Goal-Driven Execution

- **Skill** - Invoke with `/karpathy-guidelines` for detailed guidance when writing, reviewing, or refactoring code.

### frontend-design

Create distinctive, production-grade frontend interfaces with high design quality. Includes:

- **Skill** - Invoke with `/frontend-design` when building web components, pages, dashboards, or any web UI.

Focuses on bold aesthetic choices, avoiding generic "AI slop" aesthetics. Emphasizes typography, color themes, motion, spatial composition, and visual details.

### checker

Automated Pyright type checking for the eneo Python backend. Includes:

- **Stop Hook** - Automatically runs type checking when Claude finishes editing Python files in `backend/src/intric/`. Blocks and provides feedback if errors are found.

- **CLAUDE.md** - Guidelines for the ratcheting type checking strategy.

- **Skill** - Invoke with `/checker` to manually run type checks.

**Configuration:**
| Environment Variable | Effect |
|---------------------|--------|
| `TYPECHECK_DISABLE=1` | Completely disable type checking |
| `TYPECHECK_WARN_ONLY=1` | Show errors but don't block |

### github-findings

Track findings, bugs, and ideas as GitHub issues on the [eneo project board](https://github.com/orgs/eneo-ai/projects/1). Designed for discovering things mid-conversation that should be tracked but not fixed right now.

- **Skill** - Invoke with `/finding` to create, list, or grab issues.

| Command | Description |
|---------|-------------|
| `/finding` | Create a new issue from a finding in the current conversation |
| `/finding list` | List all open items (Todo + In Progress) on the board |
| `/finding grab <number>` | Pick up an issue — assigns you, sets "In Progress", creates a branch |

Issues are written with structured sections (Problem, Context, Suggested Solution, Acceptance Criteria) so that Claude or another AI can understand and work on them later without extra context.

**Setup (required once per developer):**

1. Install the plugin: `/plugin install github-findings@eneoplugin`
2. Add GitHub project scope to your token:
   ```bash
   gh auth refresh -s project -h github.com
   ```
   This opens a browser where you authorize the extra scope. Only needed once.
3. Verify it works:
   ```bash
   gh project view 1 --owner eneo-ai
   ```

**Note:** The skill targets the `eneo-ai/eneo` repository and project board #1. All team members with repo access and the `project` token scope can use it.

### vikunja-kanban

Create and update Vikunja Kanban cards with safe, high-level Swedish progress updates. Includes:

- **Skill** - Invoke with `/vikunja-kanban` to create cards, link PRs, post progress updates, move tasks, and manage labels.

**Configuration:**
| Environment Variable | Effect |
|---------------------|--------|
| `VIKUNJA_BASE_URL` | Vikunja server root (no `/api/v1`) |
| `VIKUNJA_API_TOKEN` | API token (Bearer token) |
| `VIKUNJA_PROJECT_NAME` | Default project name (default: `Internal TODO`) |
| `VIKUNJA_VIEW_NAME` | Default view name (default: `Kanban`) |

## Usage

Once installed, CLAUDE.md guidelines are automatically applied. Invoke skills manually:

```
/karpathy-guidelines    # Coding guidelines
/frontend-design        # UI design guidance
/checker                # Run type checks
/finding                # Create/list/grab GitHub project issues
/vikunja-kanban         # Vikunja Kanban card management
```

## License

MIT
