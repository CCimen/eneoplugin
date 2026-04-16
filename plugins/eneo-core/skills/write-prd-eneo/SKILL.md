---
name: write-prd-eneo
description: Use when drafting or editing a PRD for Eneo. Triggers on "write PRD", "draft PRD", "new feature spec", "requirements doc", or any task under `.claude/prds/`. Enforces the Section B template (Problem/Solution/Success criteria/User stories/Acceptance/Module sketch/Testing/Out of scope/Polishing) AND Eneo-specific rules: tenancy + audit frontmatter, numeric KPIs only, no file paths in Module sketch, Swedish UX story when SvelteKit touched, security/authz story when auth surface touched.
---

# write-prd-eneo

You are drafting a PRD for Eneo (`intric/` backend + SvelteKit frontend, Swedish public-sector SaaS). PRDs live at `.claude/prds/<slug>.md` and are committed AND mirrored as a GitHub issue labeled `prd,draft`. The PRD is read by other AI agents as a programming interface — discipline matters.

## The template (non-negotiable structure)

```markdown
---
slug: <kebab-case>
created: <YYYY-MM-DD>
status: draft | approved | in-flight | shipped
tenancy_impact: none | tenant-scoped | cross-tenant
audit_impact: none | appends-to-audit | schema-change
---

# PRD: <Feature name>

## Problem statement
Pain point in the user's perspective. 1–2 sentences.

## Proposed solution
1–2 sentences.

## Success criteria (3–5 measurable KPIs)
Ban "fast", "easy", "intuitive", "modern". Require thresholds or executable commands.

## User stories (numbered, IDs required)
`US-001: As a <actor>, I want <capability>, so that <benefit>.`
Include:
- A security/authz story when the auth surface is touched.
- A Swedish-language UX + a11y story when the SvelteKit frontend is touched.
Every story must be testable.

## Acceptance criteria (checklist, per story)
Given/When/Then preferred. Cite story IDs.

## Module sketch (deep modules, Ousterhout style)
List modules + their interface shape. NO file paths, NO code snippets.

## Testing decisions
- What makes a good test here (external behavior, not internals).
- Which modules get unit / integration / e2e.
- Prior art references (existing `intric/tests/` patterns).
- Mutation-score floor for changed files (default 70%).

## Non-functional requirements
Performance, security, Swedish public-sector compliance (GDPR, arkivlagen where relevant), a11y (WCAG 2.1 AA).

## Out of scope
Explicit. Mandatory section.

## Polishing requirements
Error-handling harmony, delightful UX, i18n consistency. Do NOT meaningfully extend the work.

## Open questions / TBD
Label anything the agent must not hallucinate.
```

## The three discipline rules (enforced by /eneo-plan Stop-hook validator)

1. **Every KPI contains a number or a concrete command.** `pyright --strict 0 errors on touched files`, `p95 < 200 ms for 10k rows`, `audit entries verified by `backend/tests/contract/test_audit_completeness.py`.
2. **`## Out of scope` must not be empty.** List at least 2 bullets — what the PRD deliberately doesn't solve.
3. **Module sketch must not contain `.py` or `.svelte` file paths.** File paths rot fast (Pocock rule); modules are described by interface shape.

## BAD → GOOD diffs

### KPIs

BAD: `Fast response times and intuitive UX.`
GOOD: `p95 < 200 ms on /api/v1/api-keys list endpoint with 10k rows; Lighthouse a11y ≥ 95 on the revoke page in Swedish locale.`

### User stories

BAD: `Users can revoke API keys.`
GOOD:
```
US-001: As a tenant admin, I want to revoke an API key immediately, so that a leaked token cannot authenticate further calls.
US-002 (authz): As a tenant user (non-admin), I must NOT see the revoke button, so that the blast radius of a compromised account is bounded to its own scopes.
US-003 (Swedish UX/a11y): As a Swedish-speaking admin using a screen reader, I can reach the revoke action via keyboard tab order with a clear `aria-label` in Swedish.
```

### Module sketch

BAD: `Add revoke endpoint in backend/src/intric/api/api_keys.py.`
GOOD:
```
APIKeyService
  - revoke(tenant_id, api_key_id, reason) -> None
  - list_active(tenant_id) -> list[APIKey]
AuditLogWriter
  - write_revoke_event(tenant_id, actor, api_key_id, reason)
Revoke page (SvelteKit)
  - Typed load fetches active keys for the tenant
  - Form action POSTs to /api/v1/api-keys/:id/revoke
  - Shows Swedish confirmation dialog
```

## Eneo-specific additions (beyond Pocock's base template)

- **Frontmatter.** `tenancy_impact` and `audit_impact` are required fields. `/eneo-new` writes them; you update if the scope shifts.
- **Bracket bump note.** If the PRD will touch `audit_log`, `tenant_id` filters, or auth middleware, state this explicitly in `Non-functional requirements`. This forces the Deep-lane adversarial review in `/eneo-verify`.
- **Prior-art reference.** In `Testing decisions`, cite a similar shipped milestone's recap under `.claude/recaps/` so the approach lineage is traceable.

## Anti-patterns to avoid (Ainna + Pocock + awesome-copilot synthesis)

| Anti-pattern | Why it hurts | Remedy |
|---|---|---|
| Theater PRD (every section filled, no falsifiable KPIs) | Burns reviewer time; creates false alignment | Enforce rule 1 (numeric KPIs) |
| Length as signal | Long PRD ≠ thought-through PRD | Aim for 1–2 pages; the section headers do the structure |
| Premature PRD (written before discovery) | Anchors on an unvalidated idea | Run `/eneo-discuss` first; only approve when confidence ≥ 90% |
| Approval theater (draft sent as "final") | Reviewers can't improve, only rubber-stamp | PRD is reviewed in plan mode via `/eneo-discuss`, not Slack |
| Dual-audience confusion (human prose + agent spec mixed) | Agents miss structured cues | Keep Module sketch interface-only; move marketing prose to the GitHub issue description |

## Where this skill fits in the workflow

```
/eneo-new <description>     ← creates PRD from template (this skill triggers)
/eneo-discuss                ← interviews + confidence gate (editing the PRD iteratively)
/eneo-plan                   ← converts PRD → phased plan (prd-to-plan-eneo skill)
/eneo-start                  ← runs waves; PRD is read-only from here on
```

Once the PRD is approved (status moves from `draft` to `approved`) **do not mutate it**. Use the `Open questions` section for anything that surfaces later; each question becomes a follow-up PRD or a scope-extension discussion.
