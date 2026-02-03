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
/vikunja-kanban         # Vikunja Kanban card management
```

## License

MIT
