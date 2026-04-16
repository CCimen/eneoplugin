---
name: prd-to-issues-eneo
description: Use after /eneo-plan to decompose a plan into AFK/HITL-tagged GitHub issues in dependency order. Triggers on "create issues from plan", "break this into tickets", "open follow-up issues". Enforces thin-vertical-slice issues (not horizontal layer issues), mandatory tenancy:* and audit:* tags, Blocked-by dependency edges, and the rule that the PRD issue is NEVER closed here.
---

# prd-to-issues-eneo

Convert `.claude/plans/<slug>.md` into a set of GitHub issues on the eneo project board. Pocock's rules (verbatim, paraphrased where Eneo-specific):

> *"Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer."*

> *"HITL (human-in-the-loop) for issues that require a human decision. AFK (autonomous) otherwise. Prefer AFK where possible."*

## Rules that MUST hold for every issue

1. **Vertical slice.** One issue = one deployable demonstrable change spanning all relevant layers.
2. **HITL / AFK tag.** HITL when tenancy model, audit schema, or authz surface changes. AFK otherwise.
3. **Tenancy tag.** `tenancy:isolated | tenancy:shared | tenancy:cross | tenancy:tenant-scoped | tenancy:none` — required on every issue.
4. **Audit tag.** `audit:none | audit:appends | audit:schema` — required on every issue.
5. **Blocked-by.** `Blocked by: #<real-issue-number>` mandatory when ordering matters. No placeholders.
6. **Parent PRD issue is never closed** here. The PRD issue is canonical and stays open until `/eneo-recap`.

## Issue body template

```markdown
## Summary
<1–2 sentences>

## Linked PRD
PRD: #<prd_issue>
Phase: <N>
Plan: `.claude/plans/<slug>.md#phase-<NN>`

## Scope
- <bullet>
- <bullet>

## Acceptance
- [ ] <Given/When/Then>
- [ ] <Given/When/Then>

## Tags
- tenancy: <tenant-scoped | shared | cross | none>
- audit: <none | appends | schema>
- mode: <AFK | HITL>

## Dependencies
Blocked by: #<issue-number> (if applicable)
```

## Creation order

1. Parse the plan; enumerate deliverables per phase.
2. Group deliverables into vertical-slice issues (typically 1–3 per phase).
3. Order by dependency (schema before service before UI before integration).
4. Create issues sequentially with `gh issue create --label ...` so you can capture returned numbers for `Blocked by:` edges.
5. Populate `current-task.json.last_issues = [N1, N2, ...]` via `eneo_task_update` so `/eneo-ship` can link back.

## AFK / HITL decision table

| Change | Mode | Reason |
|---|---|---|
| New read endpoint (no auth surface change) | AFK | Agent can land it; ratchets catch regressions |
| Schema migration adding a nullable column | AFK | Safe, reversible |
| Schema migration dropping a column | **HITL** | Destructive; human decides the two-phase plan |
| Authz surface change (new role, new dependency) | **HITL** | Security-reviewer flags; human decides |
| Audit-log schema change | **HITL** | Compliance review required |
| SvelteKit route added (no auth change) | AFK | Typed load + a11y checks catch issues |
| Multi-tenant boundary change | **HITL** | Tenancy-checker can't validate intent |

## Example

Given a plan with Phase 1 tracer bullet for `revoke-api-keys`:

```
gh issue create --title "revoke-api-keys: Phase 1 tracer bullet — endpoint + UI + test" \
  --label "prd-phase,AFK,tenancy:tenant-scoped,audit:appends" \
  --body-file issue-body.md
# returns #1234
```

Then:

```
gh issue create --title "revoke-api-keys: Phase 2 UI polish + list view" \
  --label "prd-phase,AFK,tenancy:tenant-scoped,audit:none" \
  --body "...Blocked by: #1234..."
# returns #1235
```

## Do / Don't

| Do | Don't |
|---|---|
| Open issues in dependency order so Blocked-by references exist | Open all at once with placeholder numbers |
| Tag every issue with tenancy + audit even when values are `none` | Omit tags "to reduce noise" — the PR validator fails later |
| Keep the PRD issue as the parent; link all child issues to it | Close the PRD issue when Phase 1 ships |
| Prefer AFK with strong acceptance tests | Mark HITL "to be safe" — burns human review budget |
| Use the harness's labels as-is (prd-phase, AFK, HITL, tenancy:*, audit:*) | Invent new labels per milestone |
