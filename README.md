# eneoplugin

A Claude Code plugin with AI team behavioral guidelines and skills for Eneo developers.

## Installation

### Option 1: Install from GitHub

```bash
claude plugins install CCimen/eneoplugin
```

### Option 2: Install from local path

```bash
claude plugins install /path/to/eneoplugin
```

## What's Included

### CLAUDE.md

Behavioral guidelines that are automatically loaded when working in projects that use this plugin. These guidelines help reduce common LLM coding mistakes by emphasizing:

1. **Think Before Coding** - Understand context before making changes
2. **Simplicity First** - Write the simplest solution that works
3. **Surgical Changes** - Make minimal, focused modifications
4. **Goal-Driven Execution** - Stay focused on the actual goal

### Skills

#### karpathy-guidelines

Invoke with: `/karpathy-guidelines`

Detailed coding guidelines inspired by Andrej Karpathy's observations about common LLM coding mistakes. Use when:
- Writing new code
- Reviewing pull requests
- Refactoring existing code
- Debugging issues

## Usage

Once installed, the CLAUDE.md guidelines are automatically applied. To explicitly invoke the karpathy-guidelines skill:

```
/karpathy-guidelines
```

## License

MIT
