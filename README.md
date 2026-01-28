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

## Usage

Once installed, the CLAUDE.md guidelines are automatically applied. To explicitly invoke the skill:

```
/karpathy-guidelines
```

## License

MIT
