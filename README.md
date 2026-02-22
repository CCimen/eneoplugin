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
/plugin install codex-review@eneoplugin
/plugin install gemini-review@eneoplugin
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

### codex-review

Always-on peer review via OpenAI Codex CLI. Claude automatically invokes this for plan reviews, mid-implementation code reviews, and consultations. Includes:

- **Skill** - Claude auto-invokes or use `/codex-review` manually. Three operating modes:
  - **Plan Review** — Verifies architecture before implementation (~3 iterations, `gpt-5.3-codex` with xhigh reasoning)
  - **Code Review** — Reviews git diff mid-implementation for quality, maintainability, testability (`gpt-5.3-codex-spark` with xhigh)
  - **Consultation** — Answers questions when Claude is unsure (`gpt-5.3-codex-spark` with xhigh)

- **Four Personas** — Solution Architect (always), API Consumer (endpoints), Security Reviewer (auth/permissions), Performance Analyst (queries/hot paths)

- **Eneo Context** — Includes architecture reference so Codex understands Eneo patterns

**Requires:** Codex CLI installed (`codex --version`)

### gemini-review

Architectural cross-verification via Google Gemini CLI. Claude invokes this AFTER codex-review to get an independent third perspective. Includes:

- **Skill** - Claude auto-invokes after codex-review or use `/gemini-review` manually. Operates as the third step in the review pipeline:
  ```
  Claude → Codex (primary review) → Gemini (cross-check) → Claude (synthesis)
  ```

- **Same Four Personas** — Solution Architect, API Consumer, Security Reviewer, Performance Analyst

- **Focus** — Catches blind spots that Claude and Codex may share. Provides independent architectural verification using `gemini-3.1-pro-preview`

**Requires:** Gemini CLI installed (`gemini --version`)

## Usage

Once installed, CLAUDE.md guidelines are automatically applied. Invoke skills manually:

```
/karpathy-guidelines    # Coding guidelines
/frontend-design        # UI design guidance
/checker                # Run type checks
/vikunja-kanban         # Vikunja Kanban card management
/codex-review           # Peer review via Codex CLI
/gemini-review          # Cross-check via Gemini CLI
```

## License

MIT
