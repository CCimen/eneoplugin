---
name: codex-review
description: >
  Always-on peer review and consultation via OpenAI Codex CLI for the Eneo codebase.
  Claude invokes this automatically when: planning architecture or implementation approaches,
  reviewing code changes mid-implementation, unsure about design decisions, touching API
  endpoints or auth/permissions, or needing a second opinion on any non-trivial work.
  Acts as a constant "big brother" reviewer ensuring code quality, maintainability,
  security, and performance across all Eneo development.
allowed-tools: "Bash(codex exec:*),Bash(git diff:*),Bash(git status:*),Read"
---

# Codex Review — Always-On Peer Review for Eneo

Codex is your constant big brother. It watches, reviews, and verifies your work throughout
the entire development lifecycle — planning, coding, and when you need help making decisions.

## When to Invoke

**ALWAYS invoke this skill when:**

1. **Planning** — You are designing an approach, making architectural decisions, or writing
   a plan. Always run ~3 iterations before finalizing.
2. **After coding** — You have made a meaningful batch of changes (edited multiple files,
   implemented a feature or significant part of one). Send the actual diff to Codex for review.
3. **Unsure about anything** — You are choosing between approaches, unsure about edge cases,
   or need validation on a design decision. Ask Codex.
4. **Touching APIs** — Any router, endpoint, request/response model, or OpenAPI documentation.
5. **Touching auth/security** — Authentication, authorization, API keys, permissions, scopes.
6. **Performance-sensitive code** — Database queries, bulk operations, hot paths.

**Do NOT invoke for:**
- Trivial formatting, typos, or translation-only changes
- Simple file reads or exploration
- When the user explicitly says to skip review

## Three Operating Modes

### Mode 1: Plan Review

**When:** During or after planning, before implementation begins.

**What Claude sends to Codex:**
- The full proposed plan or architectural approach
- Files that will be modified and why
- Key decisions made and alternatives considered
- Eneo architecture context (relevant sections from references/eneo-context.md)

**Iterations:** ~3
1. Present the full plan with all context
2. Incorporate feedback, present revised plan — ask Codex to confirm fixes and flag anything missed
3. Final validation — ask for explicit approval or remaining blockers

**Model:** `gpt-5.3-codex` with `xhigh` reasoning (deep thinking for architecture)

### Mode 2: Code Review (Mid-Implementation)

**When:** After making a meaningful batch of code changes. Trigger this after editing
multiple files or completing a logical unit of work.

**What Claude sends to Codex:**
- `git diff` output showing all changes (run `git diff` for unstaged, `git diff --cached` for staged)
- `git status` showing the full picture of modified files
- Explanation of what was implemented and the reasoning behind key decisions
- Eneo architecture context relevant to the changed files

**What Codex reviews:**
- Maintainability and code quality
- Testability — can this be easily tested? Are there missing test cases?
- Pattern compliance — does this follow Eneo conventions?
- Edge cases — what could go wrong?
- Potential improvements — what would make this better?
- Overall implementation quality

**Iterations:** 1-3 depending on severity of findings
- If Codex finds BLOCKERs: fix and re-submit for another round
- If only WARNINGs/SUGGESTIONs: incorporate what makes sense, explain deferrals

**Model:** `gpt-5.3-codex-spark` with `xhigh` reasoning (quick feedback loop)

### Mode 3: Consultation (Ask Codex for Help)

**When:** Claude is stuck, unsure about an approach, or needs a second opinion on anything.

**What Claude sends to Codex:**
- The specific question or decision point
- Full context: what Claude is working on, what files are involved, what the task requires
- Options Claude sees with pros/cons of each
- What Claude is leaning toward and why
- Eneo architecture context relevant to the question

**Iterations:** Usually 1 (question -> answer), more if the answer raises new questions.

**Model:** `gpt-5.3-codex-spark` with `xhigh` reasoning

## Four Personas

Claude selects which personas to activate based on what's being reviewed.
Multiple personas can be active simultaneously. Solution Architect is always active.

### 1. Solution Architect (ALWAYS ACTIVE)

Evaluates maintainability, code quality, and implementation approach. Finds the balance
between not overengineering and doing the right amount of thorough work. Not shy about
recommending extra effort when it genuinely improves quality, robustness, reliability,
error handling, or testability.

**Lens questions:**
- Does this follow existing Eneo patterns (router -> service -> repo -> table)?
- Is the layering correct? Is DI wired properly through the Container?
- Are we creating unnecessary abstractions or missing necessary ones?
- Will this be easy to test and maintain in 6 months?
- Is audit logging present for all new actions? (MANDATORY in Eneo)
- Are custom exceptions used correctly and mapped to proper HTTP codes?
- Is Pyright type safety maintained?

### 2. API Consumer (when touching endpoints)

Evaluates developer experience from the perspective of someone consuming the Eneo API.
Activated when changes touch `*_router.py`, `*_models.py`, OpenAPI docs, or response schemas.

**Lens questions:**
- If I were consuming this API, what would I expect this endpoint to do?
- Are the Swagger/OpenAPI docs clear? Do they include examples and descriptions?
- Are error messages actionable? Do they tell the consumer what went wrong and how to fix it?
- Are HTTP status codes correct and conventional?
- Is naming intuitive (endpoint paths, field names, query params)?
- Is pagination, filtering, and sorting consistent with existing Eneo patterns?
- Are request/response schemas well-documented with Field descriptions?

### 3. Security Reviewer (when touching auth/permissions)

Evaluates security from an attacker's perspective. Activated when changes touch
`auth_*`, `api_key_*`, `roles/`, permissions, federation, tenant boundaries, or
any security-sensitive functionality.

**Lens questions:**
- Can a user escalate permissions through this path?
- Is there data leakage across tenant boundaries?
- Are inputs validated and sanitized at the boundary?
- Are auth guards (`require_resource_permission_for_method`, `require_api_key_scope_check`,
  `require_api_key_permission`, `require_permission`) properly applied?
- Is audit logging present for security-relevant actions?
- Are rate limits and IP restrictions enforced where needed?
- Could an API key with limited scope access resources outside its scope?

### 4. Performance Analyst (when performance matters)

Evaluates time complexity, code simplicity, and efficiency. Activated when changes
involve database queries, pagination, bulk operations, or hot-path code.

**Lens questions:**
- Are there N+1 query patterns? (e.g., loading related objects in a loop)
- Is pagination efficient (keyset/cursor vs offset)?
- Are there unnecessary database round-trips that could be batched?
- Could this be simplified without losing correctness?
- Are there obvious bottlenecks under load?
- Is the code beautiful in its simplicity while still being reliable?

## Prompt Construction

Claude MUST provide full context to Codex in every invocation. Never send bare questions
without surrounding context. Codex runs in the same project directory and can read files,
but the prompt should be self-contained enough to give Codex a clear picture.

### Prompt Template

```
## Identity
This is Claude (claude-opus-4-6) requesting a peer review from Codex.

## Mode
[PLAN REVIEW | CODE REVIEW | CONSULTATION]

## Task Context
[What Claude is working on — task description, branch name, current step in the plan]

## [Mode-specific content]

### For PLAN REVIEW:
#### Proposed Plan
[The full plan with architectural decisions, file list, approach rationale]

### For CODE REVIEW:
#### Changes Made
[git status output]
[git diff output — key sections, not necessarily the entire diff if very large]

#### Implementation Rationale
[What was implemented and why — key decisions explained]

### For CONSULTATION:
#### Question
[The specific decision point or area of uncertainty]

#### Options Considered
[What Claude sees as the options, with pros/cons]

#### Current Leaning
[What Claude is leaning toward and why]

## Eneo Architecture Context
[Relevant sections from references/eneo-context.md — only include sections
pertinent to the current review, not the entire file]

## Active Personas
Review through the following persona lenses: [Solution Architect, API Consumer, Security Reviewer, Performance Analyst — as applicable]

## Review Request
For each active persona, provide:
1. **Issues found** — with severity: BLOCKER (must fix) / WARNING (should fix) / SUGGESTION (nice to have)
2. **Specific recommendations** — with code-level detail where applicable
3. **Verdict** — APPROVED, APPROVED WITH CHANGES, or NEEDS REVISION

Be direct and concise. If the approach is solid, say so briefly and move on.
Do not pad with filler or repeat what was already stated.
```

## Model Selection

| Mode | Model | Reasoning | Rationale |
|------|-------|-----------|-----------|
| Plan Review | `gpt-5.3-codex` | `xhigh` | Deep architectural thinking |
| Code Review | `gpt-5.3-codex-spark` | `xhigh` | Quick feedback on changes |
| Consultation | `gpt-5.3-codex-spark` | `xhigh` | Fast answers to questions |

Always use `xhigh` reasoning effort. There is no reason to use lower effort.

## Command Reference

### Initial Review (Plan)

```bash
codex exec --skip-git-repo-check \
  -C <project-directory> \
  -m gpt-5.3-codex \
  -c model_reasoning_effort="xhigh" \
  -s read-only \
  --full-auto \
  "<constructed prompt>" 2>/dev/null
```

### Initial Review (Code / Consultation)

```bash
codex exec --skip-git-repo-check \
  -C <project-directory> \
  -m gpt-5.3-codex-spark \
  -c model_reasoning_effort="xhigh" \
  -s read-only \
  --full-auto \
  "<constructed prompt>" 2>/dev/null
```

### Resume for Iteration

When iterating on a review, resume the previous Codex session to maintain context.
Pipe the follow-up prompt via stdin:

```bash
echo "<follow-up prompt with incorporated feedback or clarifications>" | \
  codex exec --skip-git-repo-check resume --last 2>/dev/null
```

**Note on resume:** The resumed session inherits model, reasoning effort, and sandbox
mode from the original invocation. Do not pass those flags again unless you need to
override them.

### Getting Changes for Code Review

Before constructing a code review prompt, gather the changes:

```bash
git -C <project-directory> status
git -C <project-directory> diff
git -C <project-directory> diff --cached
```

Include the relevant output in the prompt under "Changes Made".

## Iteration Protocol

### Planning (~3 iterations, always)

| Iteration | Purpose | What to Send |
|-----------|---------|--------------|
| 1 | Initial review | Full plan + all context + all relevant personas |
| 2 | Refine | Revised plan incorporating feedback + "confirm fixes, flag anything missed" |
| 3 | Final sign-off | Final plan + "explicit approval or remaining blockers only" |

### Code Review (1-3 iterations)

| Iteration | Purpose | What to Send |
|-----------|---------|--------------|
| 1 | Initial code review | git diff + git status + rationale + relevant personas |
| 2 (if needed) | Address concerns | Updated diff after fixes + "review the changes addressing [items]" |
| 3 (if needed) | Final sign-off | Final state + "any remaining concerns?" |

### When to Stop Iterating

- Codex gives explicit approval (APPROVED) with no BLOCKERs
- All BLOCKER and WARNING items have been addressed
- Remaining items are SUGGESTION-level and Claude has consciously accepted or deferred them
- Maximum iterations reached (3)

## Integrating Feedback

After receiving Codex's response, Claude MUST:

1. **Acknowledge** every BLOCKER and WARNING item explicitly
2. **Incorporate** changes that improve the plan or implementation
3. **Push back** if Claude disagrees — state the reasoning clearly. Claude is not subservient
   to Codex. If Claude has good reasons to disagree, it should say so and optionally resume
   the Codex session to discuss: "This is Claude. I disagree with [X] because [evidence].
   What's your perspective?"
4. **Report to user** a brief summary: "Codex review complete. Flagged N items.
   Incorporated: [list]. Deferred: [list with reasons]."

**Never blindly apply all suggestions.** Use engineering judgment. Codex is a peer, not
an authority.

## Reading Eneo Context

Before constructing the first Codex prompt in a session, read the reference file:

```
.claude/skills/codex-review/references/eneo-context.md
```

(When running as an installed plugin, this will be at the plugin's installed path.)

Include ONLY the sections relevant to the current review — not the entire file.
This keeps the Codex prompt focused and within token limits.

## Prompt Size Guidelines

- **Code review (quick):** Keep under 4000 tokens. Include key diff sections, not entire files.
- **Plan review (deep):** Up to 8000 tokens is acceptable for complex architectural reviews.
- **Consultation:** Keep concise — 1000-3000 tokens. State the question clearly with enough context.
- Always include file paths so Codex can read the full files if needed (it has read-only access).
- If the git diff is very large, summarize and include only the most significant sections.
  Reference file paths for Codex to read the rest.

## Thinking Tokens

By default, suppress thinking tokens (stderr) with `2>/dev/null` to avoid bloating
Claude Code's context. Only show stderr if debugging Codex behavior or if the user
explicitly requests to see thinking output.
