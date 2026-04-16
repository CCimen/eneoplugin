# Future private-overlay architecture

**Status:** Not shipped in v1. All architectural decisions below are present in v1 so the overlay can be added later at zero rework cost.

The public `eneo-agent-harness` is a generic multi-tenant public-sector harness. A private overlay (tentatively `eneo-ai/eneo-agent-harness-private`) would layer **municipality-specific stricter policies** (e.g., Sundsvall) on top of the public marketplace without forking it.

## The three patterns that enable this

### C1. Stackable marketplaces

Claude Code's `extraKnownMarketplaces` field accepts multiple sources. The overlay ships its own marketplace and chains after the public one:

```json
{
  "extraKnownMarketplaces": {
    "eneo-agent-harness":         { "type": "github", "repo": "eneo-ai/eneo-agent-harness" },
    "eneo-agent-harness-private": { "type": "github", "repo": "eneo-ai/eneo-agent-harness-private" }
  }
}
```

Nothing in the v1 public repo hardcodes marketplace ordering; overlays install alongside.

### C2. Rule IDs + priorities

Every rule file under `docs/eneo-repo-baseline/rules/*.md` (and the Eneo repo copy) is given frontmatter:

```yaml
---
id: eneo.audit.v1
priority: 0
paths: ["backend/src/intric/audit/**"]
---
```

The overlay ships the same rule IDs with `priority: 10`. Claude Code's native rule-merger may not honor `priority` today; when that conflict matters, a small pre-load script (`.claude/hooks/session-start-merge-rules.sh`) de-dupes by `id` and picks the highest priority. Zero cost in v1; full flexibility later.

### C3. No municipality-specific values in v1 public files

Every configurable value lives in a committed-but-overridable JSON config under `.claude/config/`. The canonical example is `.claude/config/findings.json`:

```json
{
  "github_repo": "eneo-ai/eneo",
  "project_owner": "eneo-ai",
  "project_number": 1,
  "project_id": "PVT_kwDODE-ils4BRhtq",
  "status_field_id": "PVTSSF_lADODE-ils4BRhtqzg_VEKg",
  "status_options": { "todo": "f75ad846", "in_progress": "47fc9ee4", "done": "98236657" },
  "labels": ["bug", "enhancement", "documentation", "question"],
  "language": "sv",
  "board_name": "Eneo Findings"
}
```

The public `finding` skill reads these values at every invocation; it does not embed them. A municipality fork ships its own `.claude/config/findings.json` with different IDs. Zero plugin code changes required.

### Marking extraction candidates in v1

Every value that **looks** municipality-specific during v1 development is marked with `<!-- PRIVATE-OVERLAY-CANDIDATE -->` (Markdown) or `# PRIVATE-OVERLAY-CANDIDATE` (shell/Python). When the overlay ships, these are the extraction seams.

Current v1 extraction candidates (tracked here so future agents can find them):

- `.claude/config/findings.json` — already extracted in v1.
- Swedish-language prompts in `plugins/eneo-findings/skills/finding/SKILL.md` — extracted via `config.language`.
- The bootstrap flow in `session-start-bootstrap.sh` references `eneo-ai/eneo-agent-harness`. An overlay marketplace name lives in `.claude/settings.json`, not in the hook — no extraction needed.

If you add a new municipality-specific default during v1 development, add the `PRIVATE-OVERLAY-CANDIDATE` comment and document the extraction point here.

## What explicitly does NOT ship in v1

- **The private overlay repo itself.** Not created.
- **Overlay CI or versioning.** Deferred until a second municipality joins.
- **Sundsvall-stricter policies** (e.g., mandatory two-reviewer rule, stricter mutation score floor, required security sign-off) — the public mutation floor is 70%; Sundsvall overlay would ship a stricter rule file.
- **Internal-only reviewer integrations** (e.g., a private Codex deployment with extra RAG context on Sundsvall's codebase) — would live in overlay `plugins/eneo-review-private/`.
- **Municipality-branded onboarding** — the public bootstrap flow is generic; overlay can override it.
- **The rule-merger script** (`session-start-merge-rules.sh`) — shipped only when the first overlay conflict actually surfaces.

## Adding an overlay — what it looks like

When Sundsvall (or Örebro or Borlänge) decides to ship an overlay:

1. Create `eneo-ai/eneo-<muni>-harness-private` with the standard marketplace layout.
2. Add municipality-specific rule files with the same IDs but higher priority:
   ```yaml
   ---
   id: eneo.audit.v1
   priority: 10
   paths: ["backend/src/intric/audit/**"]
   ---
   # Stricter audit rules for Sundsvall
   # (e.g., require Swedish-language action names in audit metadata)
   ```
3. Ship a `.claude/config/findings.json` override with the municipality's project IDs.
4. If custom reviewers are wanted, create `plugins/eneo-review-<muni>/` with trigger gates that layer on top of the public `eneo-review`.
5. Developers add the overlay to `extraKnownMarketplaces` and `/plugin install eneo-review-<muni>@eneo-<muni>-harness-private`.

No fork of the public harness. No merge commits between public and overlay repos. The overlay is pure additive layering.

## Pointer — when to re-read this doc

- When the first municipality asks for "can we tighten <rule>?" — the answer is "ship an overlay".
- When adding a new `.claude/config/*.json` file — add it to the extraction-candidates list above.
- When touching a rule file — confirm it still has `id:` + `priority:` frontmatter.
- When touching `marketplace.json` — preserve the additive-layering pattern (no ordering assumptions).
