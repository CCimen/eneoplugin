---
name: gemini-review
description: >
  Architectural cross-verification via Google Gemini CLI for the Eneo codebase.
  Claude invokes this AFTER codex-review has completed to get an independent third
  perspective on architectural plans, significant code changes, or when Claude and Codex
  disagree. Gemini receives the original plan/code, Codex's feedback, and Claude's
  synthesis, then provides fresh verification through four persona lenses. Excels at
  catching architectural blind spots that two reviewers may have shared.
allowed-tools: "Bash(gemini:*),Bash(git diff:*),Bash(git status:*),Read"
---

# Gemini Review — Architectural Cross-Verification for Eneo

Gemini is the third eye. After Claude and Codex have agreed on an approach, Gemini
provides independent verification from a fresh perspective. It is NOT a replacement
for Codex — it is the cross-check step that catches shared blind spots.

## Role in the Review Pipeline

```
Claude (plans/codes)
  → Codex (primary peer review, ~3 iterations)
    → Gemini (architectural cross-check, 1-2 iterations)
      → Claude (synthesizes all feedback, reports to user)
```

Gemini always receives the FULL picture: what Claude proposed, what Codex said, and
what Claude incorporated. This gives Gemini the context to provide genuinely additive
feedback rather than repeating what Codex already covered.

## When to Invoke

**ALWAYS invoke after codex-review when:**

1. **Plan reviews** — After Codex has reviewed and Claude has finalized the plan,
   send the complete plan + Codex feedback to Gemini for architectural cross-check.
2. **Significant architectural changes** — When the code touches architecture, patterns,
   or structure (not just adding a field or fixing a bug).
3. **Claude-Codex disagreement** — When Claude and Codex disagree on an approach and
   need a tiebreaker perspective.
4. **Security-sensitive changes** — When auth, permissions, or tenant isolation is involved,
   a third reviewer adds defense-in-depth to the review process.

**Do NOT invoke for:**
- Trivial code reviews (Codex handles those alone)
- Quick consultations or questions (Codex handles those alone)
- Formatting, typos, translation-only changes
- When the user explicitly says to skip review
- When Codex already gave a clean APPROVED with no concerns

## Four Personas

Same personas as codex-review. Gemini activates them based on what's being reviewed.
Solution Architect is always active.

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

### 3. Security Reviewer (when touching auth/permissions)

Evaluates security from an attacker's perspective. Activated when changes touch
`auth_*`, `api_key_*`, `roles/`, permissions, federation, or tenant boundaries.

**Lens questions:**
- Can a user escalate permissions through this path?
- Is there data leakage across tenant boundaries?
- Are inputs validated and sanitized at the boundary?
- Are auth guards properly applied?
- Is audit logging present for security-relevant actions?
- Could an API key with limited scope access resources outside its scope?

### 4. Performance Analyst (when performance matters)

Evaluates time complexity, code simplicity, and efficiency. Activated when changes
involve database queries, pagination, bulk operations, or hot-path code.

**Lens questions:**
- Are there N+1 query patterns?
- Is pagination efficient (keyset/cursor vs offset)?
- Are there unnecessary database round-trips that could be batched?
- Could this be simplified without losing correctness?
- Are there obvious bottlenecks under load?

## Prompt Construction

Claude MUST provide the complete review context to Gemini. Gemini's value comes from
seeing the full picture — what was proposed, what Codex said, and what Claude decided.

### Cross-Check Prompt Template

```
## Identity
This is Claude (claude-opus-4-6) requesting architectural cross-verification from Gemini.

## Review Pipeline Context
This is the CROSS-CHECK step. Claude proposed an approach, Codex reviewed it through
multiple iterations, and Claude incorporated feedback. You are verifying the final result
from a fresh perspective.

## Original Plan / Approach
[The plan or code changes that Claude proposed]

## Codex Review Summary
[Codex's feedback — all BLOCKERs, WARNINGs, and SUGGESTIONs with their severity]

## Claude's Response to Codex
[What Claude incorporated, what it deferred, and why]

## Current State
[The finalized plan/approach after incorporating Codex feedback]

## Eneo Architecture Context
[Relevant sections from references/eneo-context.md]

## Active Personas
Cross-check through the following persona lenses: [Solution Architect, API Consumer,
Security Reviewer, Performance Analyst — as applicable]

## Cross-Check Request
Review this from a fresh perspective. Specifically:

1. **Agreement check** — Do you agree with the approach Claude and Codex settled on?
   State your overall verdict: CONFIRMED / CONFIRMED WITH ADDITIONS / DISAGREE

2. **Blind spot scan** — What might Claude and Codex have BOTH missed? Look for:
   - Shared assumptions that might be wrong
   - Edge cases neither reviewer considered
   - Architectural implications that emerge from a different angle
   - Simpler alternatives that weren't explored

3. **Per-persona review** — For each active persona:
   - Any additional issues not raised by Codex? Use severity: BLOCKER / WARNING / SUGGESTION
   - Points where you disagree with Codex's assessment
   - Confirmation of items Codex flagged correctly

4. **Final verdict** — CONFIRMED, CONFIRMED WITH ADDITIONS, or DISAGREE (with specifics)

Be direct. Don't repeat what Codex already said unless you disagree with it.
Focus on what's NEW from your perspective.
```

## Model

Always use `gemini-3.1-pro-preview`. No model selection needed — single model for all reviews.

## Command Reference

### Initial Cross-Check

```bash
gemini -m gemini-3.1-pro-preview \
  --approval-mode yolo \
  "<constructed prompt>" 2>/dev/null
```

- Headless mode: positional query runs non-interactively, output goes to stdout
- `--approval-mode yolo`: auto-approves file reads so Gemini can explore the codebase
- `2>/dev/null`: suppress debug/status output to keep Claude's context clean
- Gemini runs from the current working directory (same as the Eneo project)

### Resume for Iteration

When iterating on a cross-check, resume the previous Gemini session:

```bash
gemini -m gemini-3.1-pro-preview \
  --approval-mode yolo \
  -r "latest" \
  "<follow-up prompt>" 2>/dev/null
```

The resumed session maintains all previous context.

### Piping Long Prompts

For prompts that are too long for a positional argument, pipe via stdin:

```bash
echo "<long constructed prompt>" | gemini -m gemini-3.1-pro-preview \
  --approval-mode yolo 2>/dev/null
```

Or use a heredoc for multi-line prompts:

```bash
gemini -m gemini-3.1-pro-preview --approval-mode yolo - 2>/dev/null <<'PROMPT'
<multi-line prompt content>
PROMPT
```

## Iteration Protocol

### Plan Cross-Check (1-2 iterations)

| Iteration | Purpose | What to Send |
|-----------|---------|--------------|
| 1 | Full cross-check | Complete plan + Codex feedback + Claude synthesis + all relevant personas |
| 2 (if needed) | Resolve additions | Updated plan incorporating Gemini's additions + "any remaining concerns?" |

Usually 1 iteration is enough since Codex already did 3 iterations of review.
A second iteration is warranted only if Gemini flagged BLOCKERs or significant WARNINGs.

### Disagreement Resolution (2-3 iterations)

When used as a tiebreaker between Claude and Codex:

| Iteration | Purpose | What to Send |
|-----------|---------|--------------|
| 1 | Present the disagreement | Both positions with evidence + "which approach do you favor and why?" |
| 2 | Clarify | Follow up on Gemini's reasoning if needed |
| 3 (rare) | Final arbitration | If still unresolved, present to user with all three perspectives |

### When to Stop Iterating

- Gemini gives CONFIRMED verdict with no BLOCKERs
- All BLOCKER items from Gemini have been addressed
- Maximum iterations reached (2 for cross-check, 3 for disagreement)

## Integrating Gemini Feedback

After receiving Gemini's response, Claude MUST:

1. **Report the verdict** to the user:
   - CONFIRMED: "Gemini cross-check complete. Approach confirmed by all three reviewers."
   - CONFIRMED WITH ADDITIONS: "Gemini confirms the approach but identified N additional items: [list]"
   - DISAGREE: "Gemini disagrees with the Claude + Codex approach on [X]. Here are all three perspectives: [summary]. How would you like to proceed?"

2. **Handle new items** from Gemini:
   - BLOCKERs: Must be addressed before proceeding. Incorporate and optionally re-run codex-review on the changes.
   - WARNINGs: Incorporate where practical, defer with reasoning where not.
   - SUGGESTIONs: Note for the user, incorporate at discretion.

3. **Handle disagreements** with Codex:
   - Present both perspectives to the user with clear reasoning
   - State Claude's own assessment of who is more likely correct
   - Let the user decide

4. **Never let the pipeline delay action indefinitely.** If after 2 iterations there's no
   consensus, present the state of disagreement to the user and move forward with their choice.

## Reading Eneo Context

Before constructing the first Gemini prompt, read the reference file:

```
references/eneo-context.md
```

(Located in this skill's directory, or at the installed plugin path.)

Include ONLY the sections relevant to the current cross-check.

## Prompt Size Guidelines

- **Plan cross-check:** Up to 8000 tokens — includes original plan + Codex feedback + synthesis.
  This is the most context-heavy mode. If too large, summarize Codex's feedback to key items only.
- **Disagreement resolution:** 3000-5000 tokens — focused on the specific point of contention.
- Always include file paths so Gemini can read files directly if needed (it has file access via yolo mode).
- If the combined context exceeds limits, prioritize: current state > Codex BLOCKERs/WARNINGs > original plan > Codex SUGGESTIONs.
