# Eneo AI Team Guidelines

These behavioral guidelines help reduce common LLM coding mistakes. Apply them when writing, reviewing, or refactoring code.

## 1. Think Before Coding

Before writing any code:
- Understand the existing codebase structure and patterns
- Read relevant files completely before suggesting modifications
- Identify dependencies and potential side effects
- Ask clarifying questions if requirements are ambiguous

**Anti-pattern:** Jumping straight into implementation without understanding context.

## 2. Simplicity First

Write the simplest solution that solves the problem:
- Avoid premature abstractions and over-engineering
- Don't add features, error handling, or configurability beyond what's requested
- Three similar lines of code is better than a premature abstraction
- Don't design for hypothetical future requirements

**Anti-pattern:** Adding "improvements" that weren't asked for.

## 3. Surgical Changes

Make minimal, focused modifications:
- Only change what's necessary to complete the task
- Don't refactor surrounding code unless explicitly requested
- Don't add comments, docstrings, or type annotations to unchanged code
- Remove unused code completely instead of commenting it out

**Anti-pattern:** "While I'm here, let me also clean up this other thing..."

## 4. Goal-Driven Execution

Stay focused on the user's actual goal:
- Define clear success criteria before starting
- Verify changes against the original request
- If you encounter blockers, surface them immediately
- Don't get sidetracked by tangential issues

**Anti-pattern:** Solving interesting problems that weren't asked about.

---

## Quick Checklist

Before submitting code changes, verify:
- [ ] Did I read the relevant files first?
- [ ] Is this the simplest solution?
- [ ] Did I only change what was requested?
- [ ] Does this solve the user's actual goal?
