---
name: karpathy-guidelines
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria.
license: MIT
---

# Karpathy-Inspired Coding Guidelines

These guidelines are inspired by Andrej Karpathy's observations about common LLM coding mistakes. Apply them to produce cleaner, more maintainable code.

## Core Principles

### 1. Understand Before Acting

> "The most dangerous thing an LLM can do is confidently write code for a codebase it doesn't understand."

- **Read first, write second**: Always read relevant files before modifying them
- **Map dependencies**: Understand what depends on the code you're changing
- **Recognize patterns**: Follow existing conventions in the codebase
- **Ask when uncertain**: Surface assumptions instead of guessing

### 2. Embrace Simplicity

> "The best code is no code. The second best code is simple code."

- **Solve the actual problem**: Don't solve adjacent problems that weren't asked about
- **Avoid abstraction addiction**: Concrete code is often clearer than clever abstractions
- **Resist feature creep**: Adding "nice to have" features creates maintenance burden
- **Delete boldly**: Remove dead code instead of commenting it out

### 3. Make Surgical Changes

> "Every line you change is a line that could introduce a bug."

- **Minimal diff**: Change only what's necessary
- **Preserve working code**: Don't refactor things that work unless asked
- **One concern per change**: Don't mix bug fixes with refactoring
- **Test your assumptions**: Verify the change does what you intended

### 4. Define Success Clearly

> "If you can't describe what success looks like, you can't achieve it."

- **Clarify requirements upfront**: Ask questions before starting
- **Set measurable criteria**: How will you know when it's done?
- **Surface blockers immediately**: Don't hide problems hoping they'll resolve
- **Verify against goals**: Check that the solution matches the original request

## Common Anti-Patterns to Avoid

| Anti-Pattern | Better Approach |
|--------------|-----------------|
| Refactoring while fixing bugs | Separate commits for fixes and refactors |
| Adding error handling "just in case" | Handle errors that can actually occur |
| Creating utilities for one-time operations | Inline the code where it's used |
| Over-documenting obvious code | Write self-documenting code instead |
| Adding backwards compatibility shims | Just change the code directly |
| Guessing at implementation details | Read the code or ask for clarification |

## When to Apply These Guidelines

Use these guidelines when you're:
- Writing new code
- Reviewing pull requests
- Refactoring existing code
- Debugging issues
- Responding to code-related questions

## Success Metrics

Your code changes are successful when:
1. They solve the stated problem
2. They don't introduce new problems
3. They follow existing codebase patterns
4. They are as simple as possible (but no simpler)
5. The diff is minimal and focused
