# PRD and TDD workflows for agentic AI coding: a Claude Code harness playbook for the Eneo agent harness

**Document version:** v2 (merged) — structural decisions + full technical playbook in one document.
**Audience:** the Claude Code agent implementing the new `eneo-agent-harness` marketplace (replacing the current `eneoplugin`).
**Repos in scope:** `eneo-ai/eneo` (application) and `eneo-ai/eneo-agent-harness` (new marketplace).

This document is a direct implementation brief. **The core recommendation:** adopt a five-layer architecture — Standards + Spec + Execution + Quality Gate + Learning — combining disler's hook-enforced spec validators, Matt Pocock's tracer-bullet slice discipline, SuperClaude's Wave→Checkpoint→Wave primitive, Anthropic's progressive-disclosure skill layer, and Nous Research's autoreason finding that *iterative self-refinement usually makes things worse*. Everything is cited to primary sources.

The harness targets a 3-person Eneo core team plus external kommun contributors on a FastAPI + SQLAlchemy + Pydantic v2 + SvelteKit stack with mandatory audit logging and pyright strict ratcheting. Concrete commands, hooks, CLAUDE.md rules, and file conventions appear throughout, with a consolidated recommended workflow at the end.

---

## 0. Three architectural decisions that frame everything below

These are structural decisions the v1 research did not make explicit. They change **where** things live, not **what** they are. Read this section first — the rest of the document assumes these are locked in.

### 0.1 Hybrid repo strategy — slim baseline in Eneo, reusable harness in a separate marketplace

**Decision:** The harness splits into two repos:

- **`eneo-ai/eneo` (the application repo)** — contains only a **slim, source-controlled baseline**: `.claude/CLAUDE.md`, `.claude/rules/*`, `.claude/settings.json` with `extraKnownMarketplaces` pointing at the marketplace repo, and a `.claude/bootstrap.md` that tells new clones what to install. This baseline is what every developer and agent sees the moment they clone Eneo.
- **`eneo-ai/eneo-agent-harness` (new, replaces current `eneoplugin`)** — the **plugin marketplace**: all slash commands, subagents, skills, hooks, and validators. Versioned independently. Installed via `/plugin marketplace add eneo-ai/eneo-agent-harness`. Seedable into devcontainers by pre-installing during image build.

**Why this split** (aligns with Claude Code docs' own line: project `.claude/` is for shared repo-specific memory; plugins and marketplaces are for reusable capabilities across teams and projects):

| Concern | Lives in Eneo repo | Lives in harness repo |
|---|---|---|
| Rules specific to Eneo's codebase (auth invariants, audit schema) | ✓ | |
| Path-scoped rules for `intric/`, `frontend/` | ✓ | |
| Reusable slash commands (`/eneo-*`, `/finding-*`) | | ✓ |
| TDD hooks (phase-gate, bash firewall) | | ✓ |
| Subagent definitions | | ✓ |
| Skills (write-prd-eneo, fastapi-conventions) | | ✓ |
| Ratchet state files (`.claude/ratchet/*.json`) | ✓ (committed per-project) | |
| Marketplace manifest | | ✓ |

#### Eneo repo baseline layout

```
.claude/
├── CLAUDE.md                    # ≤80 lines, imports eneo-context.md
├── settings.json                # hooks + permissions + extraKnownMarketplaces
├── rules/
│   ├── eneo-context.md          # always loaded (invariants)
│   ├── fastapi-endpoints.md     # paths: backend/src/intric/api/**
│   ├── pydantic-models.md       # paths: backend/src/intric/models/**
│   ├── sveltekit-routes.md      # paths: frontend/apps/web/src/routes/**
│   ├── alembic-migrations.md    # paths: backend/alembic/**
│   └── audit-log.md             # paths: backend/src/intric/audit/**
├── state/                       # gitignored: phase, current-task.json
├── ratchet/                     # committed: coverage.json, mutation.json
├── prds/                        # committed: bracket-4 PRDs
├── plans/                       # committed: phase plans
├── phases/<slug>/               # committed: phase specs
├── recaps/                      # committed: milestone recaps
├── config/
│   └── findings.json            # board IDs etc. — overridable by private overlay
└── bootstrap.md                 # "run /plugin marketplace add ... if not installed"
```

#### Harness repo layout

```
.claude-plugin/marketplace.json   # lists plugins below
plugins/
├── eneo-core/                   # slash commands + subagents + skills
├── eneo-standards/              # hooks + validators
├── eneo-review/                 # optional: codex/gemini integrations
└── eneo-findings/               # GitHub Projects + /finding-teach
```

**Four plugins total**, down from the current seven. The plugin migration map:

| Current plugin | Disposition |
|---|---|
| `karpathy-guidelines` | **Delete.** Principles move into `eneo-context.md` paired with hooks (see Section G). |
| `checker` | **Absorb into `eneo-standards`.** Pattern is correct — its `find_repo_root()` and Stop hook become the template for all ratchet hooks. |
| `frontend-design` | **Keep as-is** in `eneo-core`. Imported Anthropic skill; no changes needed. |
| `finding` / `github-findings` | **Absorb into `eneo-findings`.** Extract hardcoded board IDs into `.claude/config/findings.json`. Add `/finding-teach`. |
| `vikunja-kanban` | **Delete.** GitHub Projects is single source of truth. Historical data stays in Vikunja; no new writes from the harness. |
| `codex-review` | **Absorb into `eneo-review`, mark optional.** Trigger only on bracket-4 + risky paths per Section E. |
| `gemini-review` | **Absorb into `eneo-review`, mark optional.** Same trigger logic as codex. |

#### Bootstrap flow for new developers

1. `git clone eneo && cd eneo`
2. Open Claude Code; `.claude/CLAUDE.md` loads automatically.
3. A `SessionStart` hook checks whether the harness is installed:
   ```bash
   # .claude/hooks/session-start-bootstrap.sh
   if ! claude plugin list 2>/dev/null | grep -q "eneo-core"; then
     cat <<EOF
   [eneo-bootstrap] Run these once to install the agent harness:
     /plugin marketplace add eneo-ai/eneo-agent-harness
     /plugin install eneo-core@eneo-agent-harness
     /plugin install eneo-standards@eneo-agent-harness
     /plugin install eneo-findings@eneo-agent-harness
   EOF
   fi
   ```
4. `.claude/settings.json` can also pre-seed the marketplace via `extraKnownMarketplaces` so the developer only runs `/plugin install`.

**Third layer reserved but not shipped in v1:** an optional `eneo-ai/eneo-agent-harness-private` overlay for Sundsvall-specific integrations (board IDs, stricter policies, private reviewer tokens). The v1 architecture must not make this hard to add later — see Decision 0.3.

### 0.2 Devcontainer dual-mode — hooks detect environment via env var

Eneo developers run the stack in a devcontainer; `uv`, `bun`, `pytest`, `pyright` all live inside. Claude Code may run on the host (reaching in via `docker exec`) or inside the container directly. Both must work.

**Decision:** All hooks support **both** execution environments:

- **Mode A (host + docker exec):** Hooks run on the developer's host machine; they `docker exec` into the devcontainer to reach `uv`, `bun`, `pytest`, `pyright`. Common today — developer has Claude Code on host, code in container.
- **Mode B (in-container):** Claude Code is attached directly to the devcontainer; hooks run inside, commands are native. Cleaner but requires Claude Code setup inside the container.

#### The shared env library — every hook sources this

```bash
# plugins/eneo-standards/hooks/lib/env.sh
set -euo pipefail

# --- Environment detection -----------------------------------------------------
# ENEO_DEVCONTAINER_MODE values: in-container | host-with-docker | native | disabled
detect_env() {
  if [[ -n "${ENEO_DEVCONTAINER_MODE:-}" ]]; then
    echo "$ENEO_DEVCONTAINER_MODE"; return
  fi
  if [[ -f /.dockerenv ]] || [[ -n "${REMOTE_CONTAINERS:-}" ]] || [[ -n "${DEVCONTAINER:-}" ]]; then
    echo "in-container"; return
  fi
  if command -v docker >/dev/null 2>&1 && \
     docker ps --format '{{.Names}}' 2>/dev/null | grep -q "eneo.*devcontainer\|eneo.*backend\|eneo.*dev"; then
    echo "host-with-docker"; return
  fi
  echo "native"
}

ENEO_CONTAINER_NAME_CACHE=""
eneo_container_name() {
  if [[ -n "$ENEO_CONTAINER_NAME_CACHE" ]]; then
    echo "$ENEO_CONTAINER_NAME_CACHE"; return
  fi
  ENEO_CONTAINER_NAME_CACHE=$(docker ps --format '{{.Names}}' 2>/dev/null \
    | grep -E "eneo.*(devcontainer|backend|dev)" | head -1)
  echo "$ENEO_CONTAINER_NAME_CACHE"
}

# --- Command wrapper -----------------------------------------------------------
# Usage: eneo_exec <workdir-relative-to-repo-root> <cmd> [args...]
eneo_exec() {
  local workdir="$1"; shift
  local mode; mode=$(detect_env)
  case "$mode" in
    disabled) return 0 ;;
    in-container|native)
      ( cd "${CLAUDE_PROJECT_DIR:-$(pwd)}/$workdir" && "$@" )
      ;;
    host-with-docker)
      local container; container=$(eneo_container_name)
      if [[ -z "$container" ]]; then
        echo "[eneo-env] no eneo devcontainer running; skipping: $*" >&2
        return 0  # fail open
      fi
      docker exec -w "/workspace/$workdir" "$container" "$@"
      ;;
  esac
}

# --- Path translation ----------------------------------------------------------
host_to_container_path() {
  local p="$1"
  local root
  root=$(git rev-parse --show-toplevel 2>/dev/null || echo "${CLAUDE_PROJECT_DIR:-$(pwd)}")
  echo "${p/$root/\/workspace}"
}

container_to_host_path() {
  local p="$1"
  local root
  root=$(git rev-parse --show-toplevel 2>/dev/null || echo "${CLAUDE_PROJECT_DIR:-$(pwd)}")
  echo "${p/\/workspace/$root}"
}

# --- Soft-fail helpers ---------------------------------------------------------
# Every hook must fail open on infrastructure errors (docker down, etc.)
# Hard-fail only on policy violations (e.g., editing tests during GREEN).
```

#### Concrete hook call-sites

```bash
# Typecheck a file (from the old checker plugin, updated)
eneo_exec "backend" uv run pyright --strict --outputjson "$FILE_REL"

# Run tests
eneo_exec "backend" uv run pytest "$TEST_PATH"

# Frontend build check
eneo_exec "frontend/apps/web" bun run check

# Mutation testing (Section D ratchet)
eneo_exec "backend" uv run mutmut run --paths-to-mutate "src/intric/$MODULE"
```

**Every hook example later in this document wraps its commands in `eneo_exec`.** Where v1-style examples show raw commands, read them as shorthand for the wrapped form.

#### Override and debug

Developers export one of:

- `ENEO_DEVCONTAINER_MODE=in-container` — force native execution (useful when Claude Code is attached directly to the container)
- `ENEO_DEVCONTAINER_MODE=host-with-docker` — force docker exec (useful when auto-detection misses the container)
- `ENEO_DEVCONTAINER_MODE=native` — run on whatever machine the hook executes on (CI, GitHub Actions)
- `ENEO_DEVCONTAINER_MODE=disabled` — no-op all `eneo_exec` calls (useful when diagnosing hook overhead)

Document in the harness README. Include a `/eneo-doctor` slash command that runs `detect_env` and reports the resolved mode plus versions of `uv`, `bun`, `pytest` from inside whichever environment was chosen — so developers can verify the setup without trial-and-error.

#### Reuse what already works

`plugins/checker/hooks/typecheck-stop.py`'s `find_repo_root()` already handles:
- Git-root detection
- Nested `~/eneo/eneo/` layouts
- Devcontainer at `/workspace`
- Fallback to `CLAUDE_PROJECT_DIR`

**Port this Python logic to the shared `env.sh`** (or keep a Python twin for hooks that prefer Python). Do not rewrite.

#### Devcontainer seeding for zero-config onboarding

Add to the Eneo devcontainer's `Dockerfile` / post-create:

```bash
# .devcontainer/post-create.sh
# Pre-install Claude Code CLI and the harness marketplace so the container is
# ready to use the moment it's built. Developers still need their own API key.
npm install -g @anthropic-ai/claude-code
mkdir -p ~/.claude
cat > ~/.claude/settings.json <<'EOF'
{
  "extraKnownMarketplaces": {
    "eneo-agent-harness": {
      "type": "github",
      "repo": "eneo-ai/eneo-agent-harness"
    }
  }
}
EOF
```

Result: a developer who opens the devcontainer for the first time runs `/plugin install eneo-core@eneo-agent-harness` and is ready.

### 0.3 Private-overlay architectural stub — plan for it, don't build it

v1 ships as a **single public repo** (`eneo-agent-harness`). But three architectural choices keep the door open for a later private overlay without rework:

**C1. Stackable marketplaces.** `.claude/settings.json` already supports multiple sources via `extraKnownMarketplaces`. Document this in the harness README with a "future private overlay" section showing the expected config:

```json
{
  "extraKnownMarketplaces": {
    "eneo-agent-harness": {"type": "github", "repo": "eneo-ai/eneo-agent-harness"},
    "eneo-agent-harness-private": {"type": "github", "repo": "eneo-ai/eneo-agent-harness-private"}
  }
}
```

No actual private repo ships in v1 — just the pattern.

**C2. Rule IDs + priorities.** Every file in `.claude/rules/` gets frontmatter:

```yaml
---
id: eneo.audit.v1
priority: 0              # overlays ship priority: 10 to win
paths: ["backend/src/intric/audit/**"]
---
```

Claude Code's native rule-merger may not honor `priority` today; adopt the convention anyway. If conflict resolution becomes real, a simple pre-load script in `.claude/hooks/session-start-merge-rules.sh` can dedupe by `id` picking highest priority. Cost today: zero. Future flexibility: full.

**C3. No municipality-specific values in v1 public files.** Extract everything configurable into `.claude/config/*.json`, committed but overridable:

```json
// .claude/config/findings.json — replaces hardcoded values in current finding plugin
{
  "github_repo": "eneo-ai/eneo",
  "project_number": 1,
  "project_id": "PVT_kwDODE-ils4BRhtq",
  "status_field_id": "PVTSSF_lADODE-ils4BRhtqzg_VEKg",
  "status_options": {
    "todo": "f75ad846",
    "in_progress": "47fc9ee4",
    "done": "98236657"
  },
  "labels": ["bug", "enhancement", "documentation", "question"],
  "language": "sv"
}
```

Every slash command and subagent reads this file instead of hardcoding values. A future `eneo-agent-harness-private` ships its own `findings.json` with Sundsvall-specific IDs; the public config stays generic for Örebro and Borlänge.

Mark anything that *looks* Sundsvall-specific during v1 development with a `# PRIVATE-OVERLAY-CANDIDATE` comment so extraction is mechanical when the overlay ships.

**What explicitly does NOT ship in v1:**

- The private overlay repo itself
- Overlay CI or versioning
- Sundsvall-stricter policies (e.g., mandatory two-reviewer rule)
- Internal-only reviewer integrations (e.g., private Codex model with extra context)
- Municipality-branded onboarding

Each of these gets a one-line mention in `docs/FUTURE_PRIVATE_OVERLAY.md` and is otherwise deferred.

---

## A. When a PRD is worth writing

There is broad cross-source consensus on **disciplined minimalism**. Sean Grove (OpenAI), quoted in Aakash Gupta's "AI PRD" piece (news.aakashg.com/p/ai-prd): *"a long written document was a sign of a human having put in a lot of work… this is how the PRD lost its way."* Birgitta Böckeler et al. in the O'Reilly Radar spec guide (oreilly.com/radar/how-to-write-a-good-spec-for-ai-agents/) add: *"For relatively simple, isolated tasks, an overbearing spec can actually confuse more than help… No need for a full PRD there."* Ainna's PRD FAQ (ainna.ai/resources/faq/prd-guide-faq) frames it as: *"Don't write a PRD if you haven't yet done the discovery work — you'll be creating false alignment around an unvalidated idea."*

### Three-lane framing (team-facing) + bracket mapping (agent-facing)

For team communication, use **Fast / Standard / Deep** lanes. For agent triage logic, use the numeric brackets. They map one-to-one:

| Lane | Bracket | Change surface | PRD artifact | Review | Execution |
|---|---|---|---|---|---|
| **Fast** | 1 | ≤ ~50 LOC, 1 file, no new dependency, no migration, no auth/ACL touch | None | None (own ratchets only) | Direct edit; hooks enforce TDD only on logic files |
| **Fast** | 2 | ≤ 200 LOC, ≤ 3 files, single bounded context in `intric/` | Inline bullet spec in prompt (5–10 lines): goals, acceptance, non-goals | None (own ratchets only) | Direct edit |
| **Standard** | 3 | 200–800 LOC, multi-file, new API surface OR new SvelteKit route OR new Pydantic model | Lightweight `SPEC.md` under `.claude/specs/<slug>/` (≤ 100 lines) | Fresh-context Claude review only | Tracer-bullet phases, 2–3 phases typical |
| **Deep** | 4 | > 800 LOC, cross-service, Alembic migration, auth/tenancy, audit-log schema change | Full PRD in `.claude/prds/<slug>.md` + plan-mode review + PR approval gate | Autoreason tournament (A/B/AB) + optional Codex/Gemini | Wave → Checkpoint → Wave, 3–6 phases |

These brackets are a synthesis of qualitative guidance in Gupta, O'Reilly, Ainna, and David Haberlah (medium.com/@haberlah/how-to-write-prds-for-ai-coding-agents-d60d72efb797) — the sources do not publish exact LOC cutoffs themselves, so treat them as a starting default the team can tune.

**Crucially, because Eneo has mandatory audit logging and multi-tenant isolation**, *any* change that touches `audit_log`, `tenant_id` filters, or auth middleware jumps a bracket: a 20-line change to the audit layer gets a full PRD, no exceptions.

Slash-command triage (`/eneo-new`) decides the lane and routes accordingly:
- **Fast** → proceeds immediately, no artifacts created
- **Standard** → `/eneo-new <slug>` (creates `SPEC.md`, short discussion, straight to execution)
- **Deep** → `/eneo-new <slug>` (full flow, Section F)

### Anti-patterns in the "write a PRD" decision itself

Ainna enumerates **theater PRDs** (*"structure without substance is theater"* — every section populated, no falsifiable criteria), **length-as-signal** (Grove's point), **premature PRDs** (written before discovery), **approval theater** (*"a PRD sent as a document is an update. A PRD reviewed as a team is an alignment tool"*), and **dual-audience confusion** (mixing human-alignment prose with agent-parsable spec in one file). Haberlah's key insight applies directly to Eneo: agent-facing specs *"function as programming interfaces"* and should therefore be different artifacts from the human-facing product doc. The harness should produce **agent specs** (machine-checkable) not legacy PRDs dressed up.

---

## B. A minimal-but-sufficient PRD template

Consensus sections across Matt Pocock (skills.sh/mattpocock/skills/write-a-prd), `github/awesome-copilot/skills/prd/SKILL.md`, `awesome-copilot/skills/breakdown-feature-prd/SKILL.md`, and Kiro's requirements.md convention:

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
Pain point in the user's perspective. 1–2 sentences. (Pocock + awesome-copilot.)

## Proposed solution
1–2 sentences. (awesome-copilot.)

## Success criteria (3–5 measurable KPIs)
Ban "fast", "easy", "intuitive", "modern". Require thresholds: "p95 latency < 200ms for 10k rows",
"mypy strict 0 errors on touched modules", "audit entries for all write endpoints verified by test".
(awesome-copilot BAD/GOOD diff, verbatim rule.)

## User stories (numbered, IDs required)
`US-001: As a <actor>, I want <capability>, so that <benefit>.`
Include a security/authz story if surface is touched. Include one story for Swedish-language
labels/accessibility when SvelteKit frontend is touched. Every story is testable.

## Acceptance criteria (checklist, per story)
Given/When/Then preferred. Cite story IDs.

## Module sketch (deep modules, Ousterhout style)
Pocock: *"Actively look for opportunities to extract deep modules that can be tested in isolation.
A deep module encapsulates a lot of functionality in a simple, testable interface which rarely changes."*
List modules + their interface shape. NO file paths, NO code snippets (*"They may end up being
outdated very quickly"* — Pocock).

## Testing decisions
- What makes a good test here (external behavior, not internals).
- Which modules get unit/integration/e2e.
- Prior art references (existing `intric/tests/` patterns).
- Mutation-score floor for changed files (see Section D).

## Non-functional requirements
Performance, security, Swedish public-sector compliance (GDPR, arkivlagen where relevant), a11y.

## Out of scope
Explicit. Mandatory section (Pocock + awesome-copilot both flag this).

## Polishing requirements (Pocock, unique)
End-of-work checks — error handling harmony, delightful UX, i18n consistency.
Do NOT meaningfully extend the work.

## Open questions / TBD
Label anything the agent must not hallucinate. (awesome-copilot: *"If the user didn't specify
a tech stack, ask or label it as TBD."*)
```

**Three discipline rules enforced by the `/eneo-plan` Stop-hook validator** (see Section F):

1. Every KPI contains a number or a concrete command (e.g. `pyright --strict`).
2. `## Out of scope` must not be empty.
3. Module sketch must not contain `.py` or `.svelte` file paths.

---

## C. PRD → plan → issues without dilution

The workflow that recurs across Pocock, BuilderMethods/agent-os, BMAD, and Kiro is a three-step decomposition with **strictly separate artifacts** that *reference* rather than duplicate content.

### File conventions (project-committed, in the Eneo repo)

```
.claude/
├── prds/<slug>.md                    # canonical; never mutated post-approval
├── plans/<slug>.md                   # tracer-bullet phases, references PRD sections
├── phases/<slug>/
│   ├── phase-01-tracer.md            # executable phase spec
│   ├── phase-02-<name>.md
│   └── ...
├── issues/<slug>.md                  # pre-GitHub-issue draft bundle (AFK/HITL tagged)
├── specs/<slug>/                     # Standard-lane changes skip PRD/plan and come here
│   └── SPEC.md
├── context/<slug>-<timestamp>.md     # fresh-context snapshots per phase
└── recaps/<slug>.md                  # post-milestone summaries
```

The slash commands, subagents, skills, and hook scripts themselves live in the harness repo (`eneo-agent-harness`), not in the Eneo repo.

### The three transitions

**PRD → plan** uses Pocock's `prd-to-plan` vertical-slice rule: *"Vertical slices, not horizontal layers. Each slice is deployable, demonstrable, and leaves the codebase working… Phase 1 is always the tracer bullet — the thinnest possible end-to-end path… No polish, no edge cases. Just the critical path."* For Eneo's FastAPI + SvelteKit stack a tracer bullet always touches schema + service + API route + SvelteKit minimal UI + one integration test. Phase count: 3–6 per Pocock.

Template per phase (derived from Pocock prd-to-plan + Kiro tasks.md + disler plan_w_team.md):

```markdown
# Phase N — <name>
**PRD:** @.claude/prds/<slug>.md#us-003 (reference, don't duplicate)
**Goal:** <thin end-to-end slice>
**Wave plan:**
- Wave 1 (parallel): schema draft, API contract draft, test skeleton
- Wave 2 (parallel, depends on W1): backend impl, frontend impl, migration
- Wave 3 (serial): integration + audit-log verification
**Deliverables:**
- [ ] <schema change> (files: <tbd>)
- [ ] <service> passing pyright strict
- [ ] <route> with authz test
- [ ] Alembic migration up/down tested
- [ ] Audit entries appearing for mutating endpoints
**Done when:** <specific observable outcome>
**Mutation-score floor:** 70% on changed `intric/<module>/` files
```

**Plan → issues** uses Pocock's `prd-to-issues` rules verbatim: *"Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer."* Classify each issue **HITL** (requires a human decision — e.g., tenancy-model change, audit-schema change) or **AFK** (can be merged autonomously); *"Prefer AFK where possible."* Create issues in dependency order; `Blocked by: #<real-issue-number>` field is mandatory. **The parent PRD issue is never closed or modified** — it stays canonical.

For Eneo specifically, add a **tenancy-risk tag** (`tenancy:isolated | tenancy:shared | tenancy:cross`) and **audit-tag** (`audit:none | audit:appends | audit:schema`) on every issue; PR template must echo these, and the `/eneo-ship` command's Stop-hook validator rejects PRs where body fields are missing.

### Why the three artifacts stay separate (anti-dilution)

BMAD's design rule (bmad-code-org): **one workflow per fresh chat**. Quote: *"Always start a fresh chat for each workflow. This prevents context limitations from causing issues."* Reinforced by Anthropic's own `code.claude.com/docs/en/best-practices`: *"Most best practices are based on one constraint: Claude's context window fills up fast, and performance degrades as it fills."* The three artifacts let the harness **load only what a given phase needs**: plan-mode session loads PRD; execution session loads phase + eneo-context.md; verification session loads phase + diff + tests.

Kiro (kiro.dev/docs/specs/) supplies the **traceability mechanism**: each phase/task cites the PRD section it implements; the `/eneo-verify` hook rejects phases with no PRD back-reference. *"Specifications are executable artifacts, not plans that get ignored."*

---

## D. Enforcing TDD when the agent can edit tests

This is the hardest problem and the one the harness must nail. The failure mode is universally acknowledged: aihero.dev/skill-test-driven-development-claude-code summarizes it as *"when the LLM's context is running low, it might just rewrite the test to make it pass instead of writing real implementation."* Yajin Zhou (yajin.org/blog/2026-03-22-why-ai-agents-break-rules/) crystallizes the principle: *"Rules say 'please follow TDD' — AI can choose to listen or not. Hooks say 'no tests, no code changes' — AI has no choice."* **Hooks, not prose rules, are the enforcement mechanism.**

All hook examples below wrap executable commands in `eneo_exec` per Decision 0.2.

### Mechanism 1 — phase-gated PreToolUse hook blocking test edits during GREEN

Store the current phase in `.claude/state/phase` (values: `RED`, `GREEN`, `REFACTOR`). A slash command toggles it. The hook pattern (adapted from Steve Kinney's "Claude Code Hook Examples", stevekinney.com/courses/ai-development/claude-code-hook-examples, and TDD Guard, github.com/nizos/tdd-guard):

```bash
#!/usr/bin/env bash
# plugins/eneo-standards/hooks/phase-gate.sh — PreToolUse:Edit|Write|MultiEdit
set -euo pipefail
source "$CLAUDE_PROJECT_DIR/.claude/hooks/lib/env.sh" 2>/dev/null || \
  source "$(dirname "$0")/lib/env.sh"

INPUT=$(cat)
PHASE=$(cat "$CLAUDE_PROJECT_DIR/.claude/state/phase" 2>/dev/null || echo "FREE")
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""')

is_test=false
case "$FILE" in
  *"/tests/"*|*"_test.py"|*"test_"*.py|*".test.ts"|*".spec.ts"|*"/__tests__/"*) is_test=true ;;
esac

if [[ "$PHASE" == "GREEN" && "$is_test" == "true" ]]; then
  echo "GREEN phase: tests are frozen. Edit src/ only. Fix: if the test is wrong, run '/eneo-start <slug> --phase red' to unfreeze." >&2
  exit 2
fi
if [[ "$PHASE" == "RED" && "$is_test" == "false" && "$FILE" == *"intric/"* ]]; then
  echo "RED phase: write the failing test first. src/ edits blocked." >&2
  exit 2
fi
exit 0
```

Registered in `.claude/settings.json` with matcher `"Edit|Write|MultiEdit"`. **Exit code must be 2** — GitHub issue anthropics/claude-code#21988 confirms exit code 1 is swallowed silently.

### Mechanism 2 — Bash firewall against hook bypass

GitHub issue anthropics/claude-code#29709: *"PreToolUse hooks only cover Edit and Write tools. File modifications via Bash (python, sed, echo) are not intercepted."* Mitigation — add a `PreToolUse:Bash` hook that greps the command for destructive operations against test paths:

```bash
#!/usr/bin/env bash
# plugins/eneo-standards/hooks/bash-firewall.sh — PreToolUse:Bash
INPUT=$(cat); CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
PHASE=$(cat "$CLAUDE_PROJECT_DIR/.claude/state/phase" 2>/dev/null || echo "FREE")
if [[ "$PHASE" == "GREEN" ]] && echo "$CMD" | grep -Eq '(sed -i|tee|>) .*(tests/|_test\.py|\.test\.ts|\.spec\.ts)'; then
  echo "Blocked: bash modification of test files during GREEN." >&2; exit 2
fi
exit 0
```

### Mechanism 3 — subagent isolation (the test writer never sees the impl plan)

From alexop.dev/posts/custom-tdd-workflow-claude-code-vue: *"Subagents enforce context isolation — the test writer cannot see implementation plans, so tests reflect actual requirements rather than anticipated code structure."* Two agents:

```yaml
# plugins/eneo-core/agents/tdd-test-writer.md
---
name: tdd-test-writer
description: Write failing tests for the RED phase. Use ONLY in RED phase. You receive the PRD
  section and acceptance criteria — never implementation details.
tools: Read, Glob, Grep, Write, Edit, Bash(pytest:*, pnpm test:*)
model: sonnet
---
1. Read acceptance criteria from the phase file.
2. Write integration test in intric/tests/ that exercises the external behavior described.
3. Run pytest <path> — test MUST fail, and with a meaningful assertion, not an import error.
4. Return "RED: <test_path> — failing as expected: <assertion>"
```

```yaml
# plugins/eneo-core/agents/tdd-impl-writer.md
---
name: tdd-impl-writer
description: Minimal implementation to pass a failing test. Use ONLY in GREEN phase.
tools: Read, Glob, Grep, Edit, Bash(pytest:*, pyright:*, ruff:*)
model: sonnet
---
1. Read the failing test path from the prompt.
2. Edit intric/ source files only. No test edits (blocked by hook anyway).
3. Smallest possible implementation to make the test pass.
4. Run pyright --strict on changed files — zero errors required.
5. Return "GREEN: <impl files> — <test> passing"
```

### Mechanism 4 — dual ratchets: coverage + mutation score

Coverage alone is insufficient. MuTAP (sciencedirect.com/science/article/abs/pii/S0950584924000739): *"the literature has acknowledged that coverage is weakly correlated with the efficiency of tests in bug detection."* Stack coverage (weak floor) with mutation testing (true signal).

- **Coverage ratchet**: store per-file line coverage in `.claude/ratchet/coverage.json`. `post-commit` hook on `main` updates; PR hook compares and fails if any file regresses. Pattern mirrors Eneo's existing pyright baseline ratchet — **re-use the same tooling idiom** so the team has one mental model.
- **Mutation-score ratchet**: `eneo_exec "backend" uv run mutmut run --paths-to-mutate src/intric/<changed_module>` on changed-files diff; require mutation score ≥ 70% (tune after calibration). Meta's ACH (engineering.fb.com/2025/09/30/security/llms-are-the-key-to-mutation-testing-and-better-compliance/) validates this scales in production. MutGen paper (arxiv.org/html/2506.02954) reports 89.5% MS achievable with feedback loops.
- **Anti-sycophancy check**: reject test files where >30% of assertions are tautological (`assert True`, `assert x == x`, `mock.return_value = X; assert mock.return_value == X`). Implementable as a `ruff` custom rule or a standalone AST check in `plugins/eneo-standards/hooks/validators/trivial_test_detector.py`.

### Mechanism 5 — staged commits (tests first, impl second)

Pre-commit hook enforces ordering via commit-message regex: on a feature branch, `test:`-prefixed commits must precede `feat:`-prefixed commits touching the same module path. Backed by TDAD (arxiv.org/html/2603.17973v1) finding that *"a vanilla agent caused 562 pass-to-pass test failures across 100 instances, an average of 6.5 broken tests per generated patch… TDD prompting paradox. TDD instructions without graph context increased regressions to 9.94%, worse than vanilla."* The staged-commit pattern gives the test-impact graph implicitly via git history.

### Do this / don't do this — TDD

| Do | Don't |
|---|---|
| Use `exit 2` in all blocking hooks | Use `exit 1` (swallowed; #21988) |
| Add a `PreToolUse:Bash` firewall | Trust `PreToolUse:Edit\|Write` alone (#29709) |
| Isolate test-writer from impl plan via subagents | Prompt "write tests and then implement X" in one turn |
| Ratchet mutation score per changed file | Ratchet global coverage only |
| Reject trivial assertions programmatically | Rely on code review to catch `expect(true).toBe(true)` |
| Keep CLAUDE.md TDD section ≤10 lines, hard-enforced by hook | Write a 200-line "please do TDD" aspirational rule (Zhou: *"300-line rule files get overridden under rapid request pressure"*) |
| Wrap all executable commands in `eneo_exec` | Hardcode `docker exec` or assume in-container execution |

---

## E. The right review cadence — and when review is counterproductive

The single most important recent finding is **NousResearch/autoreason** (github.com/NousResearch/autoreason, SHL0MS, April 12 2026): *"Iterative self-refinement fails for three structural reasons: prompt bias (models hallucinate flaws when asked to critique), scope creep (outputs expand unchecked each pass), and lack of restraint (models never say 'no changes needed')."*

SHL0MS on X (x.com/SHL0MS/status/2043415280953524404): *"iterative self-refinement with LLMs, no matter the prompt, usually makes things worse. the model hallucinates flaws to satisfy critique prompts, each pass expands scope unchecked, and models almost never decline to make changes even when they should."* Crucially, autoreason's gain **vanishes** as the generation-evaluation gap closes: *"At 60% private accuracy, autoreason's held-out gains vanish."* For Sonnet 4.6 on 77%-accuracy problems the review loop adds noise.

### Implications for Eneo's harness

1. **Default to no automated review pass.** Fast-lane (brackets 1–2) and most Standard-lane (bracket 3) changes ship after the impl agent's own pyright + tests + mutation ratchet. No separate reviewer subagent.
2. **Adversarial review only when warranted.** Trigger a review panel when the change has any of: cross-service contract change, auth/tenancy surface, audit-schema change, migration, >800 LOC. This is a hard rule, not a heuristic. In practice this means Deep-lane only.
3. **When reviewing, use the autoreason tournament structure.** Three versions: incumbent (A), adversarial revision (B), synthesis (AB). Judged by **fresh agents with no shared context via blind Borda count. "Do nothing" is always a first-class option.** Stop on two consecutive no-change rounds.
4. **Fresh context for reviewer is non-negotiable.** Anthropic's own guidance in *Best Practices for Claude Code*: *"A fresh context improves code review since Claude won't be biased toward code it just wrote."*
5. **"Do nothing" must appear on the rubric.** Absent this option, models fabricate issues (autoreason core finding).

### Counter-examples (when review IS worth it)

- **Plan review before execution** — always worth it for full PRDs (Ainna: *"A PRD reviewed as a team is an alignment tool… draft PRD, not a final one — invite stakeholders to improve it, not just approve it"*). Implemented via `/eneo-discuss` (Section F).
- **Security-sensitive code** — per disler and SuperClaude, a dedicated `security-reviewer` subagent is high-ROI precisely because hallucinated "issues" on the security side are cheap to dismiss but missed issues are expensive.
- **Swedish public-sector compliance checks** — GDPR data-retention, audit completeness, Swedish-language UX — should be a separate reviewer pass because the agent cannot self-verify policy conformance without an external checklist.

### Anti-pattern: theatrical multi-persona review

BMAD's Party Mode and SuperClaude's multi-persona flows can degenerate into theater (*"product manager says X, senior engineer says Y"* in a single session, all generated by the same context). The fix is BMAD's own rule: Party Mode must use *"real subagent spawning via Agent tool"*, not roleplay in one chat. The harness enforces this: any multi-persona review slash command spawns each persona as a separate subagent with its own fresh context and its own prompt file; no single-chat "let me now play the architect" is ever produced.

---

## F. Phased wave execution — the `/eneo-*` command lineup

### Developer-experience conventions (apply to every `/eneo-*` command)

1. **Do the obvious thing; tell the developer what you did.** If a command can infer the next step from current state (open plan, last phase, current slug), it proceeds silently and prints what it did in one line.
2. **Only prompt via AskUserQuestion when the branch is genuinely ambiguous.** Concrete rules:
   - Use it when there are multiple in-flight plans and no current slug written to `.claude/state/current-task.json`, or when `/eneo-new` triage is borderline between lanes.
   - Do **not** use it for things the harness can infer: current phase, next incomplete step, which file was just edited, which devcontainer is running.
3. **Every successful command ends with a `Next:` hint** — exactly one line, naming the likely next command. Example after `/eneo-plan`: `Next: /eneo-start` (or `Next: /eneo-start <slug>` when the current slug is ambiguous).
4. **Error messages are fix-oriented and structured three-part: _what_ / _why_ / _how to fix_.** Claude Code's stderr is surfaced back into the agent loop, so the more precise the fix hint, the fewer wasted turns. Template:
   ```
   ✗ <what happened — the symptom>
     Rule: <why — the underlying rule or failure, with a pointer into the rule file>
     Fix:  <how — the specific command, file edit, or escape hatch>
   ```
   Example for the phase-gate hook during RED:
   ```
   ✗ Blocked: attempted to edit backend/src/intric/audit/service.py during RED phase.
     Rule: RED phase requires a failing test before src/ edits (.claude/rules/eneo-context.md#tdd).
     Fix:  complete the failing test in backend/tests/ first; /eneo-start <slug> flips to GREEN
           automatically when the wave barrier clears. Escape hatch: '/eneo-start <slug> --phase green'.
   ```
5. **`/eneo-doctor` is runnable at any point** and always returns actionable output. For each issue it detects — missing tool, wrong `ENEO_DEVCONTAINER_MODE`, stale `.claude/state/current-task.json`, container down, ratchet file out of sync — it prints the exact command or file edit to fix.
6. **Stream progress; don't batch.** Long-running commands print a one-line header when they start and a one-line update as each wave/gate/ratchet completes. `/eneo-start` example: `Phase 2/3: backend + frontend impl` → `Wave 2/3 dispatching: tdd-impl-writer, sveltekit-specialist, alembic-migrator → waiting for DONE barriers…` → `Wave 2 complete: 3/3 artifacts written`. `/eneo-verify` streams `✓ pyright strict: 0 errors`, `✓ pytest: 47 passed`, `✗ mutation score: 62% (floor 70%) — run 'eneo_exec backend uv run mutmut results' to see survivors` in real time.
7. **State writes are the progress protocol.** As commands progress they update `.claude/state/current-task.json` (schema below). Subagents write scratchpad artifacts under `.claude/phases/<slug>/phase-NN-scratchpad/`. The `wave-barrier.sh` hook updates `.claude/state/current-task.json.wave_status`. This single state file is the source of truth for terminal output, interruption recovery, and the status line — designed once, written from hooks + commands, read from everywhere else.
8. **Interruption recovery.** Ctrl+C in the middle of execution never loses state. Running `/eneo-start` again reads `.claude/state/current-task.json` and prints `Resuming <slug> at Phase 2 Wave 2 (backend-dev returned DONE, sveltekit-specialist did not complete). Re-dispatching incomplete agents…` then picks up.

### `.claude/state/current-task.json` schema (the DX source of truth)

Designed once, used by hooks, commands, `/eneo-doctor`, and the status-line script. Full reference lives in `docs/STATE_SCHEMA.md`.

```json
{
  "slug": "revoke-api-keys",
  "lane": "deep",
  "bracket": 4,
  "tenancy_impact": "tenant-scoped",
  "audit_impact": "appends",
  "phase": 2,
  "phase_total": 3,
  "phase_name": "backend + frontend impl",
  "tdd_phase": "GREEN",
  "wave": 2,
  "wave_total": 3,
  "wave_status": { "1": "done", "2": "in_progress", "3": "pending" },
  "active_agents": ["tdd-impl-writer", "sveltekit-specialist"],
  "status": "in_progress",
  "started_at": "2026-04-16T12:30:00Z",
  "last_update": "2026-04-16T12:42:18Z",
  "next_hint": "/eneo-verify"
}
```

Write invariants:
- Only `/eneo-new` creates this file (with `phase: null`, `wave: null` until `/eneo-plan` fills them in).
- Only `/eneo-recap` deletes it (after archiving the milestone).
- `wave_barrier.sh` updates `wave_status` and `active_agents` atomically via `mktemp + mv`.
- `user-prompt-audit.sh` updates `last_update` on every prompt submission.
- Any hook or command that cannot parse the file falls back to showing only its own line — `jq -e` with a safe default.

### Status line (opt-in) — `plugins/eneo-standards/statusline/eneo-statusline.sh`

Claude Code's status line runs a shell script on every update. The harness ships an opt-in script that reads `.claude/state/current-task.json` and renders a two-line view. Developers enable it by adding `statusLine` to their `.claude/settings.json`; we **do not** force it because some developers have their own status lines.

Format:

- **Line 1 — session context (always):** `[Opus 4.7] 📁 eneo | 🌿 feature/revoke-api-keys | 42% ctx | $0.18 | 12m`
- **Line 2 — harness state (only when `.claude/state/current-task.json` exists):**  `revoke-api-keys · Phase 2/3 · Wave 2/3 [▓▓▓░░] · GREEN · 🔨 tdd-impl-writer, sveltekit-specialist`

Rules:

- Context % in line 1 is color-coded: green <70%, yellow 70–89%, red ≥90%.
- TDD phase in line 2 is color-coded: red `RED`, green `GREEN`, yellow `REFACTOR`, plain `FREE`.
- Progress bar `[▓▓▓░░]` has one block per wave in the current phase: filled for `done`, half-block `▒` for `in_progress`, empty `░` for `pending`.
- `active_agents` show only when the list is non-empty.
- Idle state — after a command completes and no agents are running — line 2 shows `revoke-api-keys · Phase 2/3 complete · Next: /eneo-verify`.
- No milestone in flight → line 2 is hidden entirely (do not show an empty bar).
- Devcontainer awareness: if `detect_env` returns `host-with-docker`, append `🐳` after the model name. If the container is expected but missing, show `🐳⚠` — failed devcontainer is immediately visible.
- Cache git calls using the `session_id` pattern from Claude Code docs; `git branch --show-current` in Eneo is slow enough to notice when the status line runs every 300 ms.
- Parse `current-task.json` defensively with `jq -e`. A malformed state file must never crash the status line; it silently falls back to line 1 only.

Testing hint (lives in the harness README):

```sh
echo '{"model":{"display_name":"Opus 4.7"},"workspace":{"current_dir":"/workspace/eneo"},"context_window":{"used_percentage":42},"cost":{"total_cost_usd":0.18,"total_duration_ms":720000},"session_id":"test"}' \
  | ./plugins/eneo-standards/statusline/eneo-statusline.sh
```

### Command naming heritage and merges

The command names adopt the short **`/eneo-*`** verb scheme. The prefix namespaces for Slack/PR greppability; the verb carries meaning (`/eneo-plan`, `/eneo-ship`) so developers understand the intent on first read. Three commands that the original draft separated have been **merged** because the split was an artifact of early thinking rather than a real developer workflow:

- `/gsd-triage` + `/gsd-new-spec` + `/gsd-new-milestone` → **one command `/eneo-new`** whose behavior branches on the detected lane.
- `/gsd-execute-phase` → **one command `/eneo-start`** that resumes a plan from wherever it left off; invocation forms decide which phase runs.

Naming heritage: **oh-my-claudecode deep-dive clarification** — Yeachan-Heo's project uses `/oh-my-claudecode:*` or `/omc-*` namespaces, not `/gsd-*`. The earlier `/gsd-*` proposal was inspired by oh-my-claudecode's *shape* but is a new design implemented on Anthropic's native primitives (Task tool, Stop-hook validators, skill progressive disclosure). The wave-execution vocabulary is taken from `barkain/claude-code-workflow-orchestration` (github.com/barkain/claude-code-workflow-orchestration) and SuperClaude's PLANNING.md Wave→Checkpoint→Wave pattern.

### `/eneo-new` — triage + entry-point for Fast / Standard / Deep lanes

*Location:* `plugins/eneo-core/commands/eneo-new.md`. Reads the user's request (`$ARGUMENTS`) and classifies against the lane table in Section A. Writes `{lane, bracket, slug, tenancy_impact, audit_impact}` to `.claude/state/current-task.json`, then branches on lane:

- **Fast** → prompts the developer: "proceed directly to editing, or create a minimal SPEC.md first?" Default is direct; SPEC is one press away if the change grows.
- **Standard** → creates `.claude/specs/<slug>/SPEC.md` (≤100 lines, bullet-style). No plan-mode tournament, no multi-phase breakdown. A single tracer-bullet phase is typical. Developer continues with `/eneo-start`.
- **Deep** → creates `.claude/prds/<slug>.md` (skeleton from template in Section B), empty `.claude/plans/<slug>.md`, empty `.claude/phases/<slug>/`, and `.claude/context/<slug>-<timestamp>.md` snapshot seed. Invokes `gh issue create --label prd,draft` with the PRD body (Pocock pattern: PRD lives as a GitHub issue AND as a committed markdown file — Eneo needs both because external kommun contributors may not have repo-push rights). Developer continues with `/eneo-discuss` → `/eneo-plan` → `/eneo-start`.

**Bracket bump rule (Section A):** any change touching `audit_log`, `tenant_id` filters, or auth middleware is force-promoted to Deep lane, regardless of LOC.

### `/eneo-discuss` — Socratic interview + scope lockdown

Runs in plan mode (hard requirement — BuilderMethods/agent-os rule for `/shape-spec`). Uses Pocock's interview script: *"Ask the user for a long, detailed description of the problem… Explore the repo to verify their assertions… Ask whether they have considered other options… Interview the user about the implementation. Be extremely detailed and thorough… Hammer out the exact scope."* Requires a **confidence score** before allowing exit (SuperClaude 90/70 gate): ≥90% proceeds to `/eneo-plan`; 70–89% presents alternatives and asks for clarification; <70% blocks with specific questions.

### `/eneo-plan` — PRD → plan with tracer-bullet Phase 1

Produces `.claude/plans/<slug>.md` using Pocock's phase template (Section C). **Stop-hook validator** (disler's embedded-validator pattern, canonical) asserts the plan contains: `## Phase 1: Tracer Bullet`, every phase cites a PRD user-story ID, and every phase has a wave plan. Validator script:

```yaml
# plugins/eneo-core/commands/eneo-plan.md frontmatter excerpt
---
description: Turn PRD into tracer-bullet phased plan
allowed-tools: Read, Write, Edit, Glob, Grep
model: opus
hooks:
  Stop:
    - hooks:
        - type: command
          command: >-
            uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/validate_file_contains.py
            --file .claude/plans/${SLUG}.md
            --contains '## Phase 1: Tracer Bullet'
            --contains '## Out of scope'
            --contains 'PRD:'
            --contains 'Wave plan:'
---
```

If validation fails, Claude sees stderr and re-loops — the spec *cannot* be saved without required sections. This pattern is directly from disler/claude-code-hooks-mastery `plan_w_team.md` and is the single highest-ROI borrow in this document.

### `/eneo-start` — resume work → Wave → Checkpoint → Wave

One command with four invocation forms (merges the earlier `/gsd-execute-phase` into the common "let's get going" verb developers naturally reach for). Per DX convention, the harness **does the obvious thing** whenever it can:

- `/eneo-start` (no arguments)
  - **If `.claude/state/current-task.json` has a slug and there is a next incomplete phase** — resume silently, print `Resuming <slug> phase <N>.`
  - **If multiple in-flight plans exist with no current slug** — use `AskUserQuestion` to let the developer pick. Auto-highlight the most-recently-modified plan as the default.
  - **If no in-flight plans exist** — print `No in-flight plans. Run /eneo-new <description> to create one.` and exit 0.
- `/eneo-start <slug>` — resume that plan at its next incomplete phase (phase files with `status: shipped` are skipped). Silent unless ambiguity.
- `/eneo-start <slug> <phase-number>` — jump directly to a specific phase when auto-detection picks wrong (e.g., after a manual rebase).
- `/eneo-start <slug> --phase <red|green|refactor|free>` — **emergency phase override**. The only supported way for a developer to manually unfreeze the TDD phase machine when a test is genuinely wrong. Writes the value to `.claude/state/phase` and prints what it set. Error messages from hooks point here.

Once the phase is selected, it reads `.claude/phases/<slug>/phase-NN-*.md` and renders the dependency graph as ASCII (barkain pattern):

```
Wave 1 (parallel)    Wave 2 (parallel)         Wave 3 (serial)
┌─ researcher ─┐      ┌─ backend-dev ──┐
├─ architect  ─┤ ───► ├─ frontend-dev ─┤ ────► ┌─ integrator ─┐
└─ security   ─┘      └─ db-migrator  ─┘        └─ reviewer   ─┘
```

Spawns wave 1 subagents **in a single assistant turn via parallel Task tool calls** (Tim Dietrich's rule: *"Be specific about the number of sub-agents. 'Use 5 parallel tasks' is clearer than 'parallelize this work.'"*). Subagents return `DONE|<artifact-path>` only — **TaskOutput is forbidden** (barkain: *"TaskOutput is prohibited (context exhaustion). Agents write to $CLAUDE_SCRATCHPAD_DIR and return DONE|{path} only"*). Wave-completion barrier: `SubagentStop` hook counts `DONE|` returns against expected N; dispatches wave 2 when complete.

**Context passed between waves is the filesystem, not the conversation.** Each wave reads only the artifact paths it declared as inputs in the phase file. This is how the Wave → Checkpoint → Wave primitive prevents context dilution across long-running work.

**TDD phase toggle**: within each wave, the command flips `.claude/state/phase` between `RED` and `GREEN` as appropriate, triggering the hooks from Section D. Wave 1 is RED (test-writer subagents); Wave 2 is GREEN (impl-writer subagents); Wave 3 is REFACTOR (reviewer + integrator agents, both phases unlocked). The phase file is the single source of truth — developers never toggle `.claude/state/phase` manually; if the agent hits a phase-gate block and the test is genuinely wrong, it escalates to the developer rather than bypassing.

### `/eneo-verify` — ratchet gate + targeted review

Runs the following checklist and blocks ship on failure. All executable commands are wrapped in `eneo_exec`:

1. `eneo_exec "backend" uv run pyright --strict` on changed files — zero errors, enforcing existing baseline ratchet.
2. `eneo_exec "backend" uv run pytest` with Eneo's existing markers, all green.
3. Coverage ratchet: no per-file regression.
4. Mutation score ratchet: ≥70% on changed `intric/` modules (`eneo_exec "backend" uv run mutmut run`).
5. Audit-log completeness check: for every mutating endpoint touched, a test asserts an audit entry.
6. Tenancy isolation smoke test: a contract test ensures no query path leaks cross-tenant data (reuse any existing Eneo test scaffolding).
7. **Conditional adversarial review** (autoreason-style tournament, Section E). Trigger only if issue is tagged `audit:schema`, `tenancy:cross`, `authz`, or LOC > 800.

Produces `.claude/phases/<slug>/phase-NN-verify.md` with evidence (command outputs attached) — satisfies SuperClaude's Four Questions self-check: *"Are all tests passing (show output); Are all requirements met (list items); No assumptions without verification (show docs); Is there evidence."*

### `/eneo-ship` — PR creation with enforced metadata

Creates the PR via `gh pr create` with a template that **must** include `tenancy:*`, `audit:*`, `PRD: #<issue>`, `Phase: <N>`, and the verify-work evidence section. A Stop-hook validator fails ship if any field is missing. Attribution: `Co-Authored-By: Claude <noreply>` in commits (Anthropic's `attribution` settings key). PR body links to the PRD issue; PRD issue is **not** closed (Pocock rule). Comments on PRD issue auto-posted summarizing the phase result.

### `/eneo-recap` — close the loop

Only runs when all phases of a slug are `shipped`. Generates `.claude/recaps/<slug>.md` (agent-os recap convention): *"short summaries of what was built… more descriptive and context-focused than a changelog, easy to reference by both humans and AI agents."* Closes the PRD issue with a link to the recap. Archives `.claude/phases/<slug>/` to `.claude/archive/`.

### `/eneo-doctor` — actionable diagnostics, runnable at any point

Runs `detect_env`, reports the resolved mode, and prints the versions of `uv`, `bun`, `pytest`, and `pyright` from inside whichever environment was chosen. First command a new developer runs after installing the harness — and the command they run whenever something feels off.

Every detected issue comes with the exact fix:

| Detected issue | Fix printed |
|---|---|
| `uv` missing on host but `ENEO_DEVCONTAINER_MODE=native` | `export ENEO_DEVCONTAINER_MODE=host-with-docker` or `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Devcontainer not running (`host-with-docker` + no container) | `docker compose -f .devcontainer/docker-compose.yml up -d` |
| `.claude/state/current-task.json` references a slug whose plan file is missing | `rm .claude/state/current-task.json` (stale) |
| Ratchet file missing but `.claude/ratchet/` exists | `uv run plugins/eneo-standards/hooks/validators/ratchet_check.py --init` |
| `claude plugin list` missing `eneo-core` | `/plugin install eneo-core@eneo-agent-harness` |
| Pyright version below pinned floor | `uv lock --upgrade-package pyright` in backend/ |

`/eneo-doctor` ends with a `Next:` hint: if the environment is clean, the next command is whichever workflow step the slug is waiting on (`/eneo-new`, `/eneo-start`, `/eneo-verify`, etc.) inferred from state.

### Files, hooks, and agent prompts — at a glance

| Command | Lane | Creates | Triggers hooks | Invokes agents |
|---|---|---|---|---|
| `/eneo-new` | Fast | `.claude/state/current-task.json` (+ optional SPEC prompt) | — | — |
| `/eneo-new` | Standard | `.claude/specs/<slug>/SPEC.md` | Stop validator on SPEC contents | — |
| `/eneo-new` | Deep | PRD, plan, phases dir, context snapshot, GH issue | Stop validator on PRD sections | — |
| `/eneo-discuss` | Deep | filled PRD | plan-mode only; confidence gate | Explore subagent (read-only) |
| `/eneo-plan` | Deep | plan.md | Stop validator on section contents | planner, architect |
| `/eneo-start` | any | phase artifacts in scratchpad | PreToolUse phase-gate; Bash firewall; SubagentStop wave barrier | tdd-test-writer, tdd-impl-writer, domain specialists |
| `/eneo-verify` | any | verify.md with evidence | PostToolUse on test commands | Conditional autoreason panel (A/B/AB judges) |
| `/eneo-ship` | any | PR | Stop validator on PR body fields | — |
| `/eneo-recap` | Deep | recap.md | — | learning-extractor (Section G) |
| `/eneo-prune` | admin | — | — | — |
| `/eneo-doctor` | admin | — | — | — |
| `/finding-teach` | any | `plugins/eneo-findings/skills/<name>/` draft + evals | — | learning-extractor |

---

## G. Sharing learnings across team machines — git as sync

The team needs learnings to flow across three core developers' machines plus external contributors. The best-documented patterns are SuperClaude's Reflexion (`pm_agent/reflexion.py`, *"cross-session learning"*), Anthropic/skills transcript mining (*"If all 3 test cases resulted in the subagent writing a create_docx.py, that's a strong signal the skill should bundle that script. Write it once, put it in scripts/"*), and agent-os's per-spec recaps. **The common mechanism is git.**

### `/finding-teach` — extract a skill from a session

After a session, the developer runs `/finding-teach <short-description>`. The command:

1. Reads the current transcript.
2. Invokes a `learning-extractor` subagent (fresh context) which proposes a candidate skill: `name`, "pushy" `description` (Anthropic skills doc: *"Claude has a tendency to undertrigger skills… please make the skill descriptions a little bit 'pushy'"*), trigger keywords, 200–400 line body.
3. Writes it to `plugins/eneo-findings/skills/<name>/SKILL.md` as a draft.
4. Requires the developer to add a ≥3-query eval file in `plugins/eneo-findings/skills/<name>/evals.md` (scaled-down Anthropic 20-query methodology: 2 should-trigger + 1 near-miss should-not-trigger as a minimum quality bar).
5. Commits on a branch of the harness repo; team reviews via PR; merge propagates the skill to every clone after the next `/plugin update`.

### `eneo-context.md` — the shared, curated memory file

Lives at `.claude/rules/eneo-context.md` (in the Eneo repo) with frontmatter `paths: ["**/*"]` so it loads on every session. **Kept under 200 lines, hard-capped by a pre-commit hook.** Contains:

- Three non-negotiable architectural invariants (audit logging on all writes; tenancy via `tenant_id` on every query; SvelteKit routes use typed load functions).
- Three forbidden patterns (raw SQL strings; bypassing `get_current_tenant()`; `print` instead of structured logging).
- Pointer `@` imports to more detailed specialized rule files (loaded only when path matches): `.claude/rules/fastapi-endpoints.md` (paths: `backend/src/intric/api/**`), `.claude/rules/pydantic-models.md` (paths: `backend/src/intric/models/**`), `.claude/rules/sveltekit-routes.md` (paths: `frontend/apps/web/src/routes/**`).

This structure follows the Anthropic docs' path-scoped rules pattern verbatim, which keeps token budget bounded while letting deep rules kick in exactly when needed.

### Pruning — active curation, not accumulation

From SuperClaude KNOWLEDGE.md practice: *"PM Agent reviews docs older than 6 months, deletes unused, merges duplicates — active curation, not just accumulation."* Implement as a monthly `/eneo-prune` command that lists skills not triggered in 90 days (log via the `SubagentStart` hook writing to `.claude/stats/skill-usage.jsonl`) and recaps older than 6 months; human decides to archive or keep.

### Anti-pattern: the karpathy-aspirational CLAUDE.md

forrestchang/andrej-karpathy-skills (github.com/forrestchang/andrej-karpathy-skills) distills Karpathy's four principles: *"Think Before Coding. Simplicity First. Surgical Changes. Goal-Driven Execution."* These are **aspirational** — they rely on the model internalizing prose. They fail under load. The harness should include those four principles in `eneo-context.md` *only* as one-liners paired with an enforcement mechanism:

| Principle | Enforcement |
|---|---|
| Think Before Coding | Confidence gate in `/eneo-discuss` (blocks at <70%) |
| Simplicity First | LOC-delta check in `/eneo-verify` warns if delta > plan estimate × 1.5 |
| Surgical Changes | Pre-commit hook rejects commits that touch files not listed in the phase's declared `files:` field |
| Goal-Driven Execution | Every phase has a machine-checkable `Done when:` clause verified by `/eneo-verify` |

Without those hooks, the principles are decoration. This is why the current `karpathy-guidelines` plugin gets deleted — prose principles without hooks fail under load.

---

## H. The anti-pattern catalog — diagnostics and remedies

Consolidating recurring failure modes from all sources:

| Anti-pattern | Source | Diagnostic | Remedy in the harness |
|---|---|---|---|
| Test-gaming under context pressure | aihero.dev, TDD Guard | Agent commits test changes shortly before impl changes to same module | Phase-gate hook + Bash firewall + staged-commit regex |
| PRD bloat / theater | Aakash Gupta, Ainna | Long PRD with no falsifiable KPIs | `/eneo-plan` validator requires numeric KPIs |
| Plan bloat (40 subtasks for a 2-hour job) | Community consensus | Subtask count > 10 for Fast lane | `/eneo-new` routes small work around PRDs; plan validator caps Phase 1 deliverables at 8 items |
| Fake multi-persona review | BMAD party-mode design note, autoreason | Multiple personas produced in one chat | Mandatory fresh-context subagents for every persona; no roleplay in main session |
| Karpathy aspirational skills | forrestchang/andrej-karpathy-skills + Zhou | Long prose rules ignored under pressure | Each principle paired with a hook (table in Section G) |
| Iterative self-refinement degrading output | autoreason | Review panels keep "finding" new issues | Default to no review pass; tournament + Borda + "do nothing" when review triggered |
| Two-kanban problem | Implicit in claudefa.st routing | One backlog of human tasks, one of agent tasks, drift | Single `.claude/issues/` source, with HITL/AFK tags; GitHub Projects syncs view; no separate agent board |
| Context dilution across phases | BMAD fresh-chat rule, Anthropic best-practices | Performance degrades as session lengthens | `/eneo-start` spawns subagents per wave; main session holds only phase file + scratchpad paths |
| Over-parallelization | claudefa.st | 10 parallel agents for a simple feature | Wave validator requires ≥3 unrelated tasks + clean file boundaries before dispatching parallel; serial default otherwise |
| Shared-file race | Wave failure mode catalog | Two parallel agents both edit `app.ts` | Phase validator rejects wave plans with file-path overlap between agents in the same wave |
| Bleed-through context to test writer | alexop.dev | Tests echo impl plan rather than spec | Hard subagent split; test-writer prompt receives PRD section only |
| Hook bypass via Bash | GH issue #29709 | Agent uses `sed -i` on protected file | Bash firewall hook (Section D) |
| Exit-code-1 silent pass | GH issue #21988 | Blocking hook "works in tests" but not in practice | Always `exit 2` with stderr message |
| Audit-completeness drift | Eneo-specific | New endpoint shipped without audit entry | `/eneo-verify` contract test: every `@router.post/put/delete` has an audit-log assertion |
| Tenancy leak | Eneo-specific | Query returns cross-tenant data in staging | `/eneo-verify` runs tenancy smoke test; mutation testing targets `tenant_id` filter predicates |
| Devcontainer path mismatch | Eneo-specific | Hook runs `uv` on host where it isn't installed | `eneo_exec` wrapper + env detection (Decision 0.2) |
| Municipality-specific values leaking into public harness | Architectural | Sundsvall board IDs hardcoded in public plugin | `.claude/config/*.json` extraction pattern (Decision 0.3) |

---

## Recommended workflow — end-to-end

The following is the concrete, implementable harness. All names are final. Locations below are relative to either the Eneo repo (`.claude/…`) or the harness repo (`plugins/…`) as noted.

### Directory layout — harness repo (`eneo-ai/eneo-agent-harness`)

```
eneo-agent-harness/
├── .claude-plugin/marketplace.json
├── docs/
│   ├── MIGRATION.md
│   └── FUTURE_PRIVATE_OVERLAY.md
└── plugins/
    ├── eneo-core/                      # commands + subagents + skills
    │   ├── commands/
    │   │   ├── gsd-triage.md
    │   │   ├── gsd-new-spec.md
    │   │   ├── gsd-new-milestone.md
    │   │   ├── gsd-discuss-phase.md
    │   │   ├── gsd-plan-phase.md
    │   │   ├── gsd-execute-phase.md
    │   │   ├── gsd-verify-work.md
    │   │   ├── gsd-ship.md
    │   │   ├── gsd-complete-milestone.md
    │   │   ├── gsd-prune-learnings.md
    │   │   └── eneo-env-check.md
    │   ├── agents/
    │   │   ├── tdd-test-writer.md
    │   │   ├── tdd-impl-writer.md
    │   │   ├── fastapi-specialist.md
    │   │   ├── sveltekit-specialist.md
    │   │   ├── alembic-migrator.md
    │   │   ├── security-reviewer.md
    │   │   ├── audit-auditor.md
    │   │   ├── tenancy-checker.md
    │   │   ├── learning-extractor.md
    │   │   └── autoreason-judge.md
    │   └── skills/
    │       ├── write-prd-eneo/
    │       ├── prd-to-plan-eneo/
    │       ├── prd-to-issues-eneo/
    │       ├── fastapi-conventions/
    │       ├── pydantic-v2-patterns/
    │       ├── sveltekit-load-patterns/
    │       ├── audit-log-writer/
    │       └── frontend-design/        # kept as-is from current eneoplugin
    ├── eneo-standards/                 # hooks + validators
    │   └── hooks/
    │       ├── lib/
    │       │   └── env.sh              # shared detect_env + eneo_exec
    │       ├── commands/
    │       │   └── finding-teach.md
    │       ├── phase-gate.sh           # PreToolUse:Edit|Write|MultiEdit
    │       ├── bash-firewall.sh        # PreToolUse:Bash
    │       ├── protect-files.sh        # PreToolUse; .env, lockfiles
    │       ├── session-start-bootstrap.sh
    │       ├── session-start-context.sh
    │       ├── wave-barrier.sh         # SubagentStop
    │       ├── pre-compact-snapshot.sh # PreCompact; persist scratchpad
    │       ├── stop-ratchet.sh         # Stop; fail if ratchets regress
    │       ├── user-prompt-audit.sh    # UserPromptSubmit; log + tag current slug
    │       └── validators/
    │           ├── validate_file_contains.py
    │           ├── validate_new_file.py
    │           ├── trivial_test_detector.py
    │           └── pr_metadata_check.py
    ├── eneo-review/                    # optional; trigger-gated
    │   └── agents/
    │       ├── codex-reviewer.md
    │       └── gemini-reviewer.md
    └── eneo-findings/                  # GitHub Projects + /finding-teach
        ├── commands/
        │   └── finding-teach.md
        └── skills/
            └── finding/
                └── SKILL.md            # reads .claude/config/findings.json
```

### Directory layout — Eneo repo baseline (`eneo-ai/eneo`)

```
eneo/
├── .claude/
│   ├── CLAUDE.md                       # ≤80 lines
│   ├── settings.json                   # hooks + permissions + marketplaces
│   ├── bootstrap.md
│   ├── state/                          # gitignored
│   │   ├── phase                       # RED | GREEN | REFACTOR | FREE
│   │   └── current-task.json
│   ├── ratchet/                        # committed
│   │   ├── coverage.json
│   │   └── mutation.json
│   ├── prds/<slug>.md                  # committed
│   ├── plans/<slug>.md                 # committed
│   ├── phases/<slug>/                  # committed
│   ├── specs/<slug>/SPEC.md            # committed (Standard lane)
│   ├── context/<slug>-<ts>.md          # committed snapshots
│   ├── issues/<slug>.md                # AFK/HITL issue bundles
│   ├── recaps/<slug>.md                # post-milestone recaps
│   ├── config/
│   │   └── findings.json               # overridable by private overlay
│   └── rules/
│       ├── eneo-context.md             # always loaded (frontmatter: paths: ["**/*"])
│       ├── fastapi-endpoints.md        # paths: backend/src/intric/api/**
│       ├── pydantic-models.md          # paths: backend/src/intric/models/**
│       ├── sveltekit-routes.md         # paths: frontend/apps/web/src/routes/**
│       ├── alembic-migrations.md       # paths: backend/alembic/**
│       └── audit-log.md                # paths: backend/src/intric/audit/**
└── .devcontainer/
    └── post-create.sh                  # seeds claude-code + marketplace
```

### CLAUDE.md (Eneo project root `.claude/CLAUDE.md`) — hard-capped at ~80 lines

```markdown
# Eneo / intric — agent rules

## Setup (run once per clone)
If `/plugin list` does not show `eneo-core`, run:
  /plugin marketplace add eneo-ai/eneo-agent-harness
  /plugin install eneo-core@eneo-agent-harness
  /plugin install eneo-standards@eneo-agent-harness
  /plugin install eneo-findings@eneo-agent-harness

## Non-negotiable invariants
1. Every mutating endpoint writes an audit entry. Verified by tests.
2. Every DB query filters by `tenant_id` via the shared context. No exceptions.
3. Pyright strict: zero new errors on touched files (ratchet in .claude/ratchet/).
4. Mutation score ≥ 70% on changed intric/ modules.

## Forbidden
- Raw SQL strings. Use SQLAlchemy 2.0 style only.
- `print`. Use structured logging.
- Bypassing `get_current_tenant()`.
- Editing tests during GREEN phase (hook enforces).
- Editing src/ during RED phase (hook enforces).

## Workflow
/eneo-new picks the lane and creates the right artifact. Then:
  - Fast:     /eneo-new (choose "proceed") → edit → /eneo-verify → /eneo-ship
  - Standard: /eneo-new → /eneo-start → /eneo-verify → /eneo-ship
  - Deep:     /eneo-new → /eneo-discuss → /eneo-plan →
              /eneo-start (repeat per phase) → /eneo-verify → /eneo-ship → /eneo-recap

/eneo-start resumes whichever plan you're in — no args in the common case.
/eneo-doctor when anything feels off; it prints fixes.
One workflow per session. Start fresh for new milestones.

## Imports
@.claude/rules/eneo-context.md
```

`.claude/rules/eneo-context.md` holds the Karpathy principles with their paired enforcement hooks (Section G table), the three deep architectural invariants, and one section each on Swedish language/a11y and GDPR retention rules. The file is imported by CLAUDE.md so it always loads, but the specialized rules under `.claude/rules/` only load when paths match the current edit — keeping token budget bounded.

### Hook registration (`.claude/settings.json` excerpt)

```json
{
  "extraKnownMarketplaces": {
    "eneo-agent-harness": {
      "type": "github",
      "repo": "eneo-ai/eneo-agent-harness"
    }
  },
  "hooks": {
    "SessionStart":       [{"hooks": [
      {"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/session-start-bootstrap.sh"},
      {"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/session-start-context.sh"}
    ]}],
    "UserPromptSubmit":   [{"hooks": [{"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/user-prompt-audit.sh"}]}],
    "PreToolUse": [
      {"matcher":"Edit|Write|MultiEdit","hooks":[
        {"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/phase-gate.sh"},
        {"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protect-files.sh"}
      ]},
      {"matcher":"Bash","hooks":[
        {"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/bash-firewall.sh"}
      ]}
    ],
    "SubagentStop":   [{"hooks":[{"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/wave-barrier.sh"}]}],
    "PreCompact":         [{"hooks":[{"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-compact-snapshot.sh"}]}],
    "Stop":               [{"hooks":[{"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/stop-ratchet.sh"}]}]
  },
  "permissions": {
    "deny":["Read(.env)","Read(.env.*)","Bash(rm -rf *)","Bash(git push --force *)"],
    "ask": ["Bash(git push *)","Bash(alembic downgrade *)","Bash(gh pr merge *)"]
  }
}
```

Hook scripts are installed by `/plugin install eneo-standards` which drops them into a stable path the `settings.json` can reference.

### End-to-end example — adding a new SvelteKit admin page with API endpoint

1. Developer: `/eneo-new "add admin page to revoke API keys"`. Classifies as **Deep lane** (auth surface + cross-cutting), creates `.claude/prds/revoke-api-keys.md` skeleton, GitHub issue `#NNNN`, empty plan and phases. Prints: `Classified as Deep lane. Created .claude/prds/revoke-api-keys.md + issue #NNNN. Next: /eneo-discuss`.
2. `/eneo-discuss` in plan mode. Interview fills PRD. Confidence gate 92% → proceeds. Prints: `PRD confidence 92% — ready to plan. Next: /eneo-plan`.
3. `/eneo-plan` produces plan.md with 3 phases: Phase 1 tracer (service + endpoint + minimal SvelteKit button + 1 integration test), Phase 2 UI polish + list view, Phase 3 audit entries + email notification. Stop-hook validator passes: all sections present, each phase cites PRD user-story IDs. Prints: `Plan saved with 3 phases. Next: /eneo-start`.
4. `/eneo-start` (no args) — harness detects `revoke-api-keys` as the current slug, resumes silently at phase 1. Wave 1 parallel: `tdd-test-writer` subagent writes failing integration test; `architect` subagent emits `.claude/phases/revoke-api-keys/phase-01-scratchpad/api-contract.md`. Wave barrier. `.claude/state/phase` flips to GREEN. Wave 2 parallel: `tdd-impl-writer` for service + endpoint; `sveltekit-specialist` for page; `alembic-migrator` (no migration needed this phase → exits fast). Wave barrier. Wave 3: `integrator` wires everything; `audit-auditor` adds audit hook to endpoint. Prints: `Phase 1 complete. Next: /eneo-verify`.
5. `/eneo-verify`. Pyright strict ✓. Pytest ✓. Coverage ratchet ✓. Mutation score 76% ✓. Audit completeness test ✓. Tenancy smoke test ✓. Because change is tagged `authz`, adversarial review panel triggers — A/B/AB tournament, three fresh-context judges, Borda winner is incumbent A (no changes). Ship allowed. Prints: `Phase 1 verified. Next: /eneo-ship`.
6. `/eneo-ship`. PR body populated with `tenancy:tenant-scoped`, `audit:appends`, `PRD: #NNNN`, `Phase: 1`. Stop-hook validates fields. PR opens. Prints: `PR #MMMM opened. Next: /eneo-start (for phase 2) or wait for review`.
7. Repeat 4–6 for Phases 2 and 3 — `/eneo-start` silently picks up phase 2 on the next run.
8. `/eneo-recap revoke-api-keys`. Recap written. PRD issue linked and closed. Prints: `Milestone closed. Next: /eneo-new <description> for the next one`.

---

## Migration order (for the Claude Code agent implementing this)

1. **Create `eneo-ai/eneo-agent-harness` repo** with the `.claude-plugin/marketplace.json` skeleton and the four plugin folders.
2. **Port `checker`'s `find_repo_root()` + Stop-hook pattern** to `plugins/eneo-standards/hooks/lib/env.sh`. Every subsequent hook sources this. Read `plugins/checker/hooks/typecheck-stop.py` first — that function handles every environment layout we have today. Use it as the template. Do not rewrite.
3. **Build `eneo-standards` plugin** with phase-gate, bash-firewall, protect-files, wave-barrier, stop-ratchet, pre-compact hooks from Section D — all wrapped in `eneo_exec`. Validators under `hooks/validators/` in Python (UV single-file scripts per disler).
4. **Build `eneo-core` plugin** with the full `/eneo-*` command lineup (`/eneo-new`, `/eneo-discuss`, `/eneo-plan`, `/eneo-start`, `/eneo-verify`, `/eneo-ship`, `/eneo-recap`, `/eneo-prune`, `/eneo-doctor`) and subagents from Section F, plus the skills (write-prd-eneo, prd-to-plan-eneo, prd-to-issues-eneo, fastapi-conventions, pydantic-v2-patterns, sveltekit-load-patterns, audit-log-writer) and the imported `frontend-design` skill kept as-is.
5. **Build `eneo-findings` plugin** absorbing current `finding` skill; extract config to `.claude/config/findings.json`; add `/finding-teach`. Mark any Sundsvall-looking values with `# PRIVATE-OVERLAY-CANDIDATE`.
6. **Build `eneo-review` plugin** absorbing codex + gemini; trigger-gated per Section E (default off; on only for Deep lane + risky paths).
7. **In `eneo-ai/eneo` repo**, create the slim `.claude/` baseline: CLAUDE.md, rules/, settings.json with `extraKnownMarketplaces`, bootstrap.md, state/, ratchet/ directories.
8. **Delete** current `eneoplugin` plugins: `karpathy-guidelines`, `vikunja-kanban` (with a deprecation notice pointing at GitHub Projects).
9. **Update Eneo's devcontainer** `post-create.sh` script to pre-install Claude Code and seed the marketplace config.
10. **Write `docs/MIGRATION.md`** for the 3 core developers covering: what changed, what to uninstall, new slash commands, the dual-mode env var.
11. **Write `docs/FUTURE_PRIVATE_OVERLAY.md`** covering the stackable-marketplace pattern, rule-ID/priority convention, and `.claude/config/*.json` extraction points.

### Ideas adopted from each source (attribution summary)

- **Matt Pocock (skills.sh)** — PRD template sections (Problem/Solution/User Stories/Testing Decisions/Out of Scope/Polishing), `prd-to-plan` tracer-bullet rule (*"Phase 1 is always the tracer bullet… No polish, no edge cases"*), `prd-to-issues` HITL/AFK classification, deep-modules principle, rule against file paths in PRDs.
- **github/awesome-copilot** — measurable-criteria BAD/GOOD diff rule, 3–5 clarifying questions, Non-Goals section, AI-system evaluation sections, Fibonacci/t-shirt estimation (for Deep-lane PRDs).
- **Yeachan-Heo/oh-my-claudecode** — multi-phase autopilot structure (Expansion→Planning→Execution→QA→Validation), Ralph persistence-loop concept (simplified here to phase re-loops on validator failure), tiered model routing (Sonnet default, Opus for architect-level passes), pipeline/handoff contract in frontmatter, transcript-to-skill promotion.
- **github/awesome-copilot, agent-os, BMAD** — standards-as-skills, timestamp-slug specs (adapted to slug-only here for readability), HALT-at-menu in `/eneo-discuss`.
- **disler/claude-code-hooks-mastery** — **the single most copied pattern**: slash commands with embedded validator hooks in frontmatter. Builder/validator pair applied directly to `tdd-test-writer`/`tdd-impl-writer`. UV single-file hook scripts. 13-event hook coverage template.
- **SuperClaude_Framework** — Wave → Checkpoint → Wave primitive, confidence gate 90/70 thresholds, Four Questions self-check, Reflexion pattern for KNOWLEDGE/CLAUDE.md updates, 7 Red Flags language adapted into `eneo-context.md`.
- **anthropics/skills** — progressive-disclosure architecture, "pushy" skill descriptions, 20-query eval methodology (scaled down to 3), `references/<variant>.md` domain organization for FastAPI/SvelteKit/Alembic rule files, transcript-mining for `/finding-teach`.
- **bmad-code-org/BMAD-METHOD** — one-workflow-per-fresh-chat rule, Edge Case Hunter as parallel adversarial reviewer (`security-reviewer`), `bmad-help`-style intelligent-next-step recommender (via `/eneo-new`).
- **Anthropic docs + engineering blog** — exact hook schemas, path-scoped rules, CLAUDE.md hierarchy, plan-mode entry, Writer/Reviewer fresh-context pattern, git-as-progress-file pattern from *Effective harnesses for long-running agents*.
- **AWS Kiro** — three-phase Requirements→Design→Tasks adapted to PRD→Plan→Phases, traceability via PRD section references, EARS-style acceptance criteria as a recommendation for Deep-lane PRDs.
- **NousResearch/autoreason** — the autoreason tournament structure for conditional adversarial review; default-to-no-review-loop for small changes; "do nothing" as first-class rubric outcome.
- **nizos/tdd-guard, Yajin Zhou, MuTAP/MutGen/Meta ACH** — hook-enforced phase gates, mutation-score ratcheting as true-signal floor, trivial-assertion detector.
- **Karpathy (forrestchang distillation + autoresearch)** — four minimalism principles paired one-for-one with enforcement hooks to avoid the aspirational-skills anti-pattern.
- **Claude Code docs** — hybrid repo strategy (project `.claude/` for repo-specific memory; plugins and marketplaces for reusable capabilities); `extraKnownMarketplaces` stackable-source pattern.
- **Current `eneoplugin/checker` plugin** — `find_repo_root()` function, Stop-hook idiom, env-detection heuristics; reused verbatim in the new `env.sh` rather than rewritten.

---

## Conclusion — three shifts that change the outcome

First, **the harness's job is to make discipline unavoidable, not to remind the agent of it**. Yajin Zhou's summary — *"rules say 'please'… hooks say 'no, you can't'"* — is the correct design stance. Every principle in `eneo-context.md` is paired with a hook; principles without hooks are decoration and should be deleted.

Second, **context is the scarce resource and the filesystem is the right place to store it**. The Wave → Checkpoint → Wave primitive works because artifacts live in scratchpad files, not in conversation history; subagents read inputs explicitly; Task returns only `DONE|<path>`. This mirrors Kiro's *"specifications are executable artifacts, not plans that get ignored"* and Anthropic's *"most best practices are based on one constraint: Claude's context window fills up fast."*

Third, and most counter-intuitive for a team with a quality culture: **default to no review pass**. The autoreason finding — *"iterative self-refinement, no matter the prompt, usually makes things worse"* — is the biggest live update to agentic-coding best practice since extended thinking. The harness uses review as a *targeted* tool triggered only by real risk (audit, tenancy, auth, migration, large LOC) and structured as a blind tournament with "do nothing" as a valid outcome. On Fast and most Standard lane changes the impl agent's own ratchets (pyright strict, mutation score, audit completeness, tenancy smoke test) are the review; adding a second model to re-critique would degrade, not improve, quality.

Beyond the three shifts, three structural decisions (Section 0) shape where everything lives: the **hybrid repo split** keeps Eneo-specific rules close to the code and reusable machinery versioned independently; the **devcontainer dual-mode** via `eneo_exec` lets hooks work whether Claude Code runs on the host or inside the container; and the **private-overlay stub** preserves the ability to ship Sundsvall-specific stricter policies later without rework, at zero cost today.

For a 3-person core team plus external kommun contributors, this harness trades a week of setup for a permanent reduction in coordination overhead — every change either fits the Fast lane and ships after one hook pass, or it rides the PRD→plan→phase→verify→ship rails with machine-checkable gates at each step. No two-kanban problem, no PRD theater, no aspirational rules being quietly ignored under load.

### Key follow-up sources

The downstream Claude agent implementing this should start by reading, in order:
1. Existing `eneoplugin/plugins/checker/hooks/typecheck-stop.py` — proven env-detection to reuse.
2. `code.claude.com/docs/en/hooks-guide` — hook event schemas.
3. `code.claude.com/docs/en/skills` — progressive disclosure + pushy descriptions.
4. `code.claude.com/docs/en/plugins` and the marketplace docs — how `extraKnownMarketplaces` works.
5. `github.com/disler/claude-code-hooks-mastery` (specifically `commands/plan_w_team.md`) — embedded validator pattern.
6. `github.com/nizos/tdd-guard` — phase-gate reference implementation.
7. `github.com/NousResearch/autoreason` — tournament structure.
8. `skills.sh/mattpocock/skills/prd-to-issues` — HITL/AFK pattern.
9. `github.com/barkain/claude-code-workflow-orchestration` — Wave barrier via SubagentStop.
10. `github.com/github/awesome-copilot/tree/main/skills/prd` — measurable-KPI examples.

The Reddit research stream of the original project failed to retrieve primary threads — re-run those searches with direct Reddit API access to capture per-thread attribution if that level of detail is wanted before implementation.
