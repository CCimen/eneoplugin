# eneoplugin

A Claude Code plugin marketplace with AI team behavioral guidelines for Eneo developers.

## Installation

### 1. Add the marketplace

```
/plugin marketplace add CCimen/eneoplugin
```

### 2. Install the plugin

```
/plugin install karpathy-guidelines@eneoplugin
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

## Usage

Once installed, the CLAUDE.md guidelines are automatically applied. To explicitly invoke the skill:

```
/karpathy-guidelines
```

## License

MIT
