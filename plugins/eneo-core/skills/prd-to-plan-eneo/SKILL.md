---
name: prd-to-plan-eneo
description: Use when decomposing an approved PRD into phased plan. Triggers on "plan the phases", "decompose PRD", "tracer bullet", or editing files under `.claude/plans/`. Produces Pocock-style vertical slices — Phase 1 is always the thinnest end-to-end path (schema + service + API + SvelteKit + 1 integration test). Phase count 3–6. Every phase cites PRD user-story IDs and has a wave plan; /eneo-plan's Stop-hook validator rejects plans missing these.
---

# prd-to-plan-eneo

Turn `.claude/prds/<slug>.md` into `.claude/plans/<slug>.md` by slicing vertically. Pocock's rule, verbatim:

> *"Vertical slices, not horizontal layers. Each slice is deployable, demonstrable, and leaves the codebase working… Phase 1 is always the tracer bullet — the thinnest possible end-to-end path… No polish, no edge cases. Just the critical path."*

## Eneo's tracer bullet

For every Deep-lane feature the Phase-1 tracer bullet touches **all five layers**:

1. Pydantic schema
2. Service (with audit-log write if mutating)
3. API route (with authz dependency + tenant filter)
4. SvelteKit minimal UI (one button, Swedish label, typed load)
5. One integration test that exercises the slice end-to-end

If you cannot describe a Phase-1 slice that spans all five, the PRD is too ambitious for one milestone — split it.

## Phase template (one block per phase)

```markdown
# Phase <N> — <short name>
**PRD:** @.claude/prds/<slug>.md#us-<story-id>
**Goal:** <thin end-to-end slice>

**Wave plan:**
- Wave 1 (parallel): <2–4 fresh-context tasks that can run independently>
- Wave 2 (parallel, depends on W1): <impl tasks, separated by file boundaries>
- Wave 3 (serial): <integration + audit-log + adversarial review if Deep>

**Deliverables:**
- [ ] <schema change> (files: <hint, not path>)
- [ ] <service> passing pyright strict
- [ ] <route> with authz test
- [ ] Alembic migration up/down tested (when schema changes)
- [ ] Audit entries for every mutating endpoint

**Done when:** <specific observable outcome>
**Mutation-score floor:** 70% on changed `intric/<module>/` files
```

## Required structural elements (validated by the Stop-hook)

- `## Phase 1: Tracer Bullet` (heading literal)
- `## Out of scope` (per Section B discipline)
- Every phase cites at least one `PRD:` user-story ID
- Every phase has a `Wave plan:` block

Missing any of these → `/eneo-plan`'s Stop-hook fails, Claude re-edits.

## Wave sizing rules (from Section H anti-patterns)

- **Over-parallelization.** If a wave would dispatch >5 subagents or the tasks share more than one file, collapse to serial. Simple features don't need 10 parallel agents.
- **Shared-file race.** No two agents in the same wave may touch overlapping files. If overlap is necessary (e.g., two specialists editing a single router), split into serial waves.
- **Unrelated tasks in parallel only.** The Tim Dietrich rule: "Use 5 parallel tasks" beats "parallelize this work". Be explicit about the count.

## Typical phase patterns for Eneo

| Feature class | Typical phases |
|---|---|
| New admin page (Deep lane) | (1) tracer: list + revoke button; (2) filters + pagination + empty states; (3) audit trail UI + email notification |
| New public endpoint | (1) tracer: endpoint + auth + happy-path test; (2) validation + error cases; (3) rate limit + metrics |
| Cross-service migration | (1) double-write; (2) backfill + reconciliation test; (3) cutover + old-path removal |

## Do / Don't

| Do | Don't |
|---|---|
| Keep Phase 1 to 3 waves max | Plan 6-wave Phase 1 "to be thorough" — kills parallelism |
| Write mutation-score floor per phase | Leave it implicit (ratchet will bite) |
| Cite PRD user-story IDs literally (`@.claude/prds/<slug>.md#us-001`) | Paraphrase the PRD content into the plan (drift) |
| Use the phase file as the single source of truth for the wave | Copy deliverables into multiple places — updates drift |
| Declare `Done when:` in observable terms (e.g., `200 response on curl`, `audit row visible`) | Declare `Done when: feature feels complete` |

## Example (slice of revoke-api-keys plan)

```markdown
# Phase 1 — Tracer Bullet
**PRD:** @.claude/prds/revoke-api-keys.md#us-001
**Goal:** Revoke an active API key by clicking a button in the admin UI; the subsequent call using that key returns 401.

**Wave plan:**
- Wave 1 (parallel): (a) tdd-test-writer — integration test for POST /api/v1/api-keys/:id/revoke; (b) architect — API contract in phase-01-scratchpad/api-contract.md
- Wave 2 (parallel): (a) tdd-impl-writer — endpoint + APIKeyService.revoke; (b) sveltekit-specialist — revoke button on /admin/api-keys; (c) alembic-migrator — exit-fast (no migration this phase)
- Wave 3 (serial): integrator wires audit-log entry on revoke; audit-auditor verifies

**Deliverables:**
- [ ] APIKeyService.revoke(tenant_id, api_key_id, reason) -> None
- [ ] POST /api/v1/api-keys/:id/revoke returns 204
- [ ] SvelteKit revoke button with Swedish label "Återkalla"
- [ ] Integration test in backend/tests/integration/test_revoke_api_keys.py asserts 204 + DB state
- [ ] Audit row in audit_log with action=api_key.revoke

**Done when:** curl -X POST <url>/revoke returns 204 AND a subsequent auth call with the revoked key returns 401 AND audit_log has a row for the event.
**Mutation-score floor:** 70% on changed intric/services/api_key_service.py
```
