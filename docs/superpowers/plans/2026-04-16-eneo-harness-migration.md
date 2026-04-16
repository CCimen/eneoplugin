# Eneo Agent Harness Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the current `eneoplugin` marketplace (7 plugins) into the `eneo-agent-harness` structure defined in `eneo-harness-playbook.md` (4 plugins: eneo-core, eneo-standards, eneo-review, eneo-findings) with all slash commands, subagents, skills, hooks, validators, and docs as specified — strictly local, no pushes.

**Architecture:** Five-layer harness — Standards + Spec + Execution + Quality Gate + Learning — combining hook-enforced spec validators (disler), tracer-bullet slice discipline (Pocock), Wave→Checkpoint→Wave primitive (SuperClaude), progressive-disclosure skills (Anthropic), and autoreason-gated review (Nous Research). Hybrid repo strategy: this repo becomes the harness marketplace; Eneo app repo gets a slim baseline (out-of-scope for local work but documented). Devcontainer dual-mode via `eneo_exec` detection wrapper. Private-overlay architectural stub preserved.

**Tech Stack:** Claude Code plugin marketplace (`.claude-plugin/marketplace.json` + `plugins/*/...`), Markdown slash commands with YAML frontmatter, Bash hooks + Python UV single-file validators, GitHub Projects CLI, FastAPI/SQLAlchemy/Pydantic v2/SvelteKit context (from Eneo repo).

**Playbook reference:** `/Users/ccimen/eneo/eneoplugin/eneo-harness-playbook.md` — authoritative spec. Every task below cites a section.

**Scope constraints:**
- Keep everything local: no git push, no touches to Eneo app repo
- Work in-place in `/Users/ccimen/eneo/eneoplugin` (this repo acts as the future `eneo-agent-harness`)
- Old plugins stay intact through Phase 7; Phase 8 is the only destructive phase and requires user approval
- External files (Eneo repo `.claude/` baseline, devcontainer `post-create.sh`) are emitted as templates under `docs/eneo-repo-baseline/` for the user to later apply

---

## File Structure

### Harness repo (this repo, target end-state)

```
eneoplugin/
├── .claude-plugin/marketplace.json          # UPDATE: list 4 new plugins
├── docs/
│   ├── MIGRATION.md                         # NEW: Section "Migration order"
│   ├── FUTURE_PRIVATE_OVERLAY.md            # NEW: Decision 0.3
│   ├── superpowers/plans/                   # NEW: this plan lives here
│   └── eneo-repo-baseline/                  # NEW: templates to apply to Eneo repo
│       ├── CLAUDE.md                        # Section "Recommended workflow" (hard-capped ~80 lines)
│       ├── settings.json                    # Section "Hook registration"
│       ├── bootstrap.md                     # Decision 0.1 bootstrap flow
│       ├── rules/eneo-context.md            # Section G + G-principle table
│       ├── rules/fastapi-endpoints.md
│       ├── rules/pydantic-models.md
│       ├── rules/sveltekit-routes.md
│       ├── rules/alembic-migrations.md
│       ├── rules/audit-log.md
│       ├── config/findings.json             # Decision 0.3 C3
│       └── devcontainer/post-create.sh      # Decision 0.2 seeding
└── plugins/
    ├── eneo-core/                           # NEW
    │   ├── .claude-plugin/plugin.json
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
    │       ├── write-prd-eneo/SKILL.md
    │       ├── prd-to-plan-eneo/SKILL.md
    │       ├── prd-to-issues-eneo/SKILL.md
    │       ├── fastapi-conventions/SKILL.md
    │       ├── pydantic-v2-patterns/SKILL.md
    │       ├── sveltekit-load-patterns/SKILL.md
    │       ├── audit-log-writer/SKILL.md
    │       └── frontend-design/SKILL.md     # MOVED from top-level plugin
    ├── eneo-standards/                      # NEW (absorbs old checker)
    │   ├── .claude-plugin/plugin.json
    │   ├── hooks/hooks.json
    │   ├── hooks/lib/env.sh                 # Decision 0.2 shared lib
    │   ├── hooks/lib/env.py                 # Python twin (reuses checker's find_repo_root)
    │   ├── hooks/phase-gate.sh              # Section D mechanism 1
    │   ├── hooks/bash-firewall.sh           # Section D mechanism 2
    │   ├── hooks/protect-files.sh
    │   ├── hooks/session-start-bootstrap.sh # Decision 0.1 bootstrap hook
    │   ├── hooks/session-start-context.sh
    │   ├── hooks/wave-barrier.sh            # Section F SubagentStop
    │   ├── hooks/pre-compact-snapshot.sh
    │   ├── hooks/stop-ratchet.sh            # Section D mechanism 4
    │   ├── hooks/user-prompt-audit.sh
    │   ├── hooks/typecheck-stop.py          # PORTED from old checker
    │   ├── hooks/validators/validate_file_contains.py
    │   ├── hooks/validators/validate_new_file.py
    │   ├── hooks/validators/trivial_test_detector.py
    │   └── hooks/validators/pr_metadata_check.py
    ├── eneo-review/                         # NEW (absorbs old codex-review, gemini-review)
    │   ├── .claude-plugin/plugin.json
    │   └── agents/
    │       ├── codex-reviewer.md
    │       └── gemini-reviewer.md
    └── eneo-findings/                       # NEW (absorbs old finding)
        ├── .claude-plugin/plugin.json
        ├── commands/finding-teach.md
        └── skills/finding/SKILL.md          # reads .claude/config/findings.json
```

### Plugins to delete in Phase 8 (after user approval)

- `plugins/karpathy-guidelines/` (principles move into `eneo-context.md` with enforcement hooks per Section G table)
- `plugins/vikunja-kanban/` (GitHub Projects is sole source of truth per Decision 0.1)
- `plugins/checker/` (absorbed into `eneo-standards/`)
- `plugins/codex-review/` (absorbed into `eneo-review/`)
- `plugins/gemini-review/` (absorbed into `eneo-review/`)
- `plugins/finding/` (absorbed into `eneo-findings/`)
- `plugins/frontend-design/` (moved into `eneo-core/skills/`)

---

## Phase 0: Foundation (non-destructive)

**Goal:** Create the four new plugin skeletons and shared libraries alongside existing plugins. Nothing is deleted yet.

### Task 0.1: Create `eneo-standards` plugin skeleton

**Files:**
- Create: `plugins/eneo-standards/.claude-plugin/plugin.json`
- Create: `plugins/eneo-standards/hooks/hooks.json`

- [ ] **Step 1: Write plugin.json** — description: "Hook-enforced standards: TDD phase gate, bash firewall, wave barrier, ratchets, validators for Eneo"
- [ ] **Step 2: Write hooks.json** — empty shell; populated in Phase 1
- [ ] **Step 3: Verify loadable** — `ls plugins/eneo-standards/.claude-plugin/plugin.json`

### Task 0.2: Create `eneo-core` plugin skeleton

**Files:**
- Create: `plugins/eneo-core/.claude-plugin/plugin.json`

- [ ] **Step 1: Write plugin.json** — description: "Eneo slash commands (/eneo-*), subagents (tdd/specialist/reviewer), and skills (PRD, FastAPI, SvelteKit, audit-log)"
- [ ] **Step 2: Verify** — `ls plugins/eneo-core/.claude-plugin/plugin.json`

### Task 0.3: Create `eneo-review` plugin skeleton

**Files:**
- Create: `plugins/eneo-review/.claude-plugin/plugin.json`

- [ ] **Step 1: Write plugin.json** — description: "Optional adversarial review: Codex + Gemini reviewers, triggered only on Deep-lane + risky paths (auth/tenancy/audit/migration/>800 LOC)"
- [ ] **Step 2: Verify** — `ls plugins/eneo-review/.claude-plugin/plugin.json`

### Task 0.4: Create `eneo-findings` plugin skeleton

**Files:**
- Create: `plugins/eneo-findings/.claude-plugin/plugin.json`

- [ ] **Step 1: Write plugin.json** — description: "GitHub Projects findings tracker: create/list/grab issues + /finding-teach session learning extractor"
- [ ] **Step 2: Verify** — `ls plugins/eneo-findings/.claude-plugin/plugin.json`

### Task 0.5: Port `find_repo_root()` from checker into `hooks/lib/env.sh`

**Files:**
- Read: `plugins/checker/hooks/typecheck-stop.py` (lines 18–46 — `find_repo_root`)
- Create: `plugins/eneo-standards/hooks/lib/env.sh`

- [ ] **Step 1: Implement env.sh exactly per Decision 0.2** — `detect_env()`, `eneo_container_name()`, `eneo_exec()`, `host_to_container_path()`, `container_to_host_path()`, soft-fail pattern. Use the function bodies verbatim from the playbook Section 0.2.
- [ ] **Step 2: Port `find_repo_root()` logic** — git-root detection, nested `~/eneo/eneo/`, `/workspace`, `CLAUDE_PROJECT_DIR` fallback. Add as `find_repo_root` bash function.
- [ ] **Step 3: Make executable** — `chmod +x plugins/eneo-standards/hooks/lib/env.sh`
- [ ] **Step 4: Smoke test** — `bash -n plugins/eneo-standards/hooks/lib/env.sh` (syntax check)

### Task 0.6: Create `hooks/lib/env.py` Python twin

**Files:**
- Create: `plugins/eneo-standards/hooks/lib/env.py`

- [ ] **Step 1: Copy `find_repo_root`, `get_changed_python_files`, run_* helpers** from checker's `typecheck-stop.py` verbatim (lines 18–116). Add `detect_env()` and `eneo_exec()` equivalents mirroring the bash API.
- [ ] **Step 2: Smoke test** — `python3 -c "import sys; sys.path.insert(0, 'plugins/eneo-standards/hooks/lib'); import env; print(env.detect_env())"`

### Task 0.7: Update marketplace.json (additive, keeps old plugins listed)

**Files:**
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Add the 4 new plugins** (`eneo-core`, `eneo-standards`, `eneo-review`, `eneo-findings`) with correct source paths — do NOT remove old plugins yet
- [ ] **Step 2: Validate JSON** — `python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))"`

### Task 0.8: Verify Phase 0

- [ ] List plugins: all 11 directories exist (7 old + 4 new skeletons)
- [ ] marketplace.json lists all 11 (for transition)
- [ ] No existing plugin was modified except marketplace.json

**Commit point:** "Phase 0: scaffold 4 new plugin skeletons alongside existing plugins"

---

## Phase 1: Hooks & Validators (eneo-standards)

**Goal:** Port every hook and validator from Section D, Section F, and the settings.json excerpt. All hooks source `lib/env.sh` and wrap commands in `eneo_exec`.

### Task 1.1: `phase-gate.sh` — Section D Mechanism 1

**Files:**
- Create: `plugins/eneo-standards/hooks/phase-gate.sh`

- [ ] **Step 1:** Copy the bash script from playbook Section D Mechanism 1 verbatim (source env.sh, read phase from `.claude/state/phase`, block GREEN test edits and RED src edits, exit 2)
- [ ] **Step 2:** Test-file pattern matches: `*/tests/*`, `*_test.py`, `test_*.py`, `*.test.ts`, `*.spec.ts`, `*/__tests__/*`
- [ ] **Step 3:** `chmod +x`; `bash -n` syntax check

### Task 1.2: `bash-firewall.sh` — Section D Mechanism 2

**Files:**
- Create: `plugins/eneo-standards/hooks/bash-firewall.sh`

- [ ] **Step 1:** Copy bash script from playbook Section D Mechanism 2 verbatim — grep `sed -i|tee|>` against test paths during GREEN; exit 2 if matched
- [ ] **Step 2:** `chmod +x`; `bash -n`

### Task 1.3: `protect-files.sh` — PreToolUse: Edit|Write|MultiEdit

**Files:**
- Create: `plugins/eneo-standards/hooks/protect-files.sh`

- [ ] **Step 1:** Block edits to `.env`, `.env.*`, lockfiles (`bun.lockb`, `uv.lock`, `package-lock.json`), and any path matching `.claude/ratchet/*` (only commit hooks may update these). Exit 2 with explanation.
- [ ] **Step 2:** `chmod +x`; `bash -n`

### Task 1.4: `session-start-bootstrap.sh` — Decision 0.1

**Files:**
- Create: `plugins/eneo-standards/hooks/session-start-bootstrap.sh`

- [ ] **Step 1:** Copy from Decision 0.1 Bootstrap flow step 3 verbatim — if `claude plugin list` does not show `eneo-core`, print install instructions.
- [ ] **Step 2:** `chmod +x`; `bash -n`

### Task 1.5: `session-start-context.sh`

**Files:**
- Create: `plugins/eneo-standards/hooks/session-start-context.sh`

- [ ] **Step 1:** If `.claude/state/current-task.json` exists, echo its contents to stderr so Claude sees current-lane/slug. Soft-fail if missing.
- [ ] **Step 2:** If `.claude/rules/eneo-context.md` exists, emit `[eneo-bootstrap] loaded eneo-context.md from <path>`.
- [ ] **Step 3:** `chmod +x`; `bash -n`

### Task 1.6: `wave-barrier.sh` — Section F SubagentStop

**Files:**
- Create: `plugins/eneo-standards/hooks/wave-barrier.sh`

- [ ] **Step 1:** Read the current wave expected count from `.claude/state/wave.json` (`{wave: N, expected: M, done: K}`). Increment `done`. If `done >= expected`, write status `ready-for-next-wave` and exit 0. If not yet ready, exit 0 silently.
- [ ] **Step 2:** `chmod +x`; `bash -n`

### Task 1.7: `pre-compact-snapshot.sh`

**Files:**
- Create: `plugins/eneo-standards/hooks/pre-compact-snapshot.sh`

- [ ] **Step 1:** On PreCompact event, copy `CLAUDE_SCRATCHPAD_DIR` (or `.claude/phases/<current-slug>/scratchpad/`) to `.claude/context/<slug>-<timestamp>.md` so wave artifacts survive compaction.
- [ ] **Step 2:** `chmod +x`; `bash -n`

### Task 1.8: `stop-ratchet.sh` — Section D Mechanism 4

**Files:**
- Create: `plugins/eneo-standards/hooks/stop-ratchet.sh`

- [ ] **Step 1:** Source env.sh. If ratchet files exist at `.claude/ratchet/coverage.json` and `.claude/ratchet/mutation.json`, run coverage + mutmut via `eneo_exec`, compare per-file floors; if any file regresses, `exit 2` with an error showing the regression.
- [ ] **Step 2:** Soft-fail (exit 0) if tooling is missing (uv/mutmut absent). Hard-fail only on policy regression.
- [ ] **Step 3:** `chmod +x`; `bash -n`

### Task 1.9: `user-prompt-audit.sh`

**Files:**
- Create: `plugins/eneo-standards/hooks/user-prompt-audit.sh`

- [ ] **Step 1:** On UserPromptSubmit, if `.claude/state/current-task.json` has a slug, emit a system-visible context line tagging the slug. Also append the prompt hash + timestamp to `.claude/stats/prompts.jsonl`.
- [ ] **Step 2:** `chmod +x`; `bash -n`

### Task 1.10: Port `typecheck-stop.py` into eneo-standards

**Files:**
- Read: `plugins/checker/hooks/typecheck-stop.py`
- Create: `plugins/eneo-standards/hooks/typecheck-stop.py`

- [ ] **Step 1:** Copy checker's `typecheck-stop.py` verbatim into eneo-standards. Update `from lib.env import ...` to use `env.py` path.
- [ ] **Step 2:** Verify no behavior change — same `TYPECHECK_DISABLE` / `TYPECHECK_WARN_ONLY` env vars, same `find_repo_root` logic.

### Task 1.11: `validators/validate_file_contains.py` — disler embedded-validator pattern

**Files:**
- Create: `plugins/eneo-standards/hooks/validators/validate_file_contains.py`

- [ ] **Step 1:** UV single-file script per playbook Section F `/eneo-plan` excerpt. Parse `--file <path>` and repeated `--contains <string>` flags. Exit 2 with error for each missing string.
- [ ] **Step 2:** Include UV script header:
  ```python
  # /// script
  # requires-python = ">=3.11"
  # ///
  ```
- [ ] **Step 3:** `chmod +x`; verify: `uv run plugins/eneo-standards/hooks/validators/validate_file_contains.py --help`

### Task 1.12: `validators/validate_new_file.py`

**Files:**
- Create: `plugins/eneo-standards/hooks/validators/validate_new_file.py`

- [ ] **Step 1:** Parse `--path <glob>` and `--must-not-exist`. Used by `/eneo-milestone` to fail if PRD file already exists before creation. UV single-file script.
- [ ] **Step 2:** `chmod +x`

### Task 1.13: `validators/trivial_test_detector.py` — Section D Mechanism 4 anti-sycophancy

**Files:**
- Create: `plugins/eneo-standards/hooks/validators/trivial_test_detector.py`

- [ ] **Step 1:** UV single-file script using `ast` module. For each `assert` node in changed test files, classify as trivial if: `assert True`, `assert x == x`, `mock.return_value = X; assert mock.return_value == X`. Fail with exit 2 if >30% of assertions are trivial.
- [ ] **Step 2:** `chmod +x`

### Task 1.14: `validators/pr_metadata_check.py` — Section F /eneo-ship

**Files:**
- Create: `plugins/eneo-standards/hooks/validators/pr_metadata_check.py`

- [ ] **Step 1:** UV single-file script. Parses PR body via `gh pr view <n> --json body`. Require presence of regex patterns: `tenancy:(isolated|shared|cross|tenant-scoped|none)`, `audit:(none|appends|schema)`, `PRD: #\d+`, `Phase: \d+`, and a `## Verify evidence` section.
- [ ] **Step 2:** Exit 2 with specific missing-field message if any absent.
- [ ] **Step 3:** `chmod +x`

### Task 1.15: Write `hooks/hooks.json`

**Files:**
- Modify: `plugins/eneo-standards/hooks/hooks.json`

- [ ] **Step 1:** Register hooks per playbook "Hook registration" excerpt. Matchers: `Edit|Write|MultiEdit` → phase-gate + protect-files; `Bash` → bash-firewall; `SessionStart` → bootstrap + context; `UserPromptSubmit` → audit; `SubagentStop` → wave-barrier; `PreCompact` → snapshot; `Stop` → ratchet (+ typecheck).
- [ ] **Step 2:** Use `${CLAUDE_PLUGIN_ROOT}` for hook paths per plugin-dev best practice.
- [ ] **Step 3:** Validate JSON — `python3 -c "import json; json.load(open('plugins/eneo-standards/hooks/hooks.json'))"`

### Task 1.16: Status line — `plugins/eneo-standards/statusline/eneo-statusline.sh`

**Files:**
- Create: `plugins/eneo-standards/statusline/eneo-statusline.sh`

- [ ] **Step 1:** Two-line output per playbook Section F "Status line (opt-in)" — line 1 session context, line 2 harness state from `.claude/state/current-task.json`.
- [ ] **Step 2:** Line 1 fields: `[<model>] <docker-icon> 📁 <cwd> | 🌿 <branch> | <N>% ctx | $<cost> | <duration>`. Color: ctx% green<70, yellow 70-89, red≥90.
- [ ] **Step 3:** Line 2 only when `current-task.json` exists: `<slug> · Phase N/total · Wave N/total [▓▓▓░░] · <TDD phase> · 🔨 <active_agents>`. Omit wave/phase/agents segments when fields are empty. Idle state shows `Next: <next_hint>` instead of agents.
- [ ] **Step 4:** Cache `git branch --show-current` keyed by `session_id` under `${TMPDIR}/eneo-statusline-cache/`.
- [ ] **Step 5:** Devcontainer awareness: append `🐳` when `detect_env` returns `host-with-docker`; `🐳⚠` when container is expected but missing.
- [ ] **Step 6:** Defensive jq reads (`jq -re`) — malformed state never crashes the status line; falls back to line 1 only.

### Task 1.17: Phase 1 verification

- [ ] All 9 hook shell scripts exist, are executable, pass `bash -n` syntax check
- [ ] All 5 Python validators exist (validate_file_contains, validate_new_file, trivial_test_detector, pr_metadata_check, ratchet_check) and show `--help`
- [ ] `typecheck-stop.py` ported; imports the shared `env` lib
- [ ] `hooks.json` valid JSON and references all files with `${CLAUDE_PLUGIN_ROOT}`
- [ ] `lib/env.sh` and `lib/env.py` exist with parity (detect_env + eneo_exec + find_repo_root)
- [ ] `statusline/eneo-statusline.sh` exists, is executable, renders line 1 on empty JSON, renders line 2 only when state file present
- [ ] `wave-barrier.sh` writes both `.claude/state/wave.json` AND updates `.claude/state/current-task.json.wave_status` + `active_agents`
- [ ] Every hook error message uses the 3-part structure (what/rule/fix)

**Commit point:** "Phase 1: eneo-standards hooks, validators, and status line (ported checker, TDD phase-gate, bash firewall, wave barrier, ratchet, validators, statusline)"

---

## Phase 2: Slash Commands (eneo-core) — the final 9 `/eneo-*` + `/finding-teach`

**Goal:** Implement the merged command set from playbook Section F with embedded validator hook frontmatter per disler's pattern.

**DX rules that apply to EVERY command (Section F "Developer-experience conventions"):**

1. Do the obvious thing; tell the developer what you did. Only prompt via `AskUserQuestion` when the branch is genuinely ambiguous (e.g., multiple in-flight plans with no current slug; borderline-lane triage in `/eneo-new`).
2. Every successful command prints a one-line `Next: /eneo-<verb>` hint at the end — inferred from state where possible.
3. Error messages are fix-oriented: the text names the specific command or file edit that resolves the error.
4. `AskUserQuestion` is **not** used for things the harness can infer: current phase, next incomplete step, which file was just edited, which devcontainer is running.

Each command file uses the YAML frontmatter convention from plugin-dev `command-development` skill: `description`, `argument-hint`, `allowed-tools`, `model`, and (where Section F specifies) a `hooks.Stop` block pointing at `validate_file_contains.py`.

### Task 2.1: `/eneo-new` — merged triage + Fast/Standard/Deep entry point

**Files:**
- Create: `plugins/eneo-core/commands/eneo-new.md`

- [ ] **Step 1:** Frontmatter — `description: Triage + create the right artifact for Fast/Standard/Deep lane. Lane is inferred; developer is prompted only when it is genuinely borderline.`; `argument-hint: "<description of the change>"`; `allowed-tools: Read, Write, Bash(gh issue create:*, git:*)`; `model: sonnet`.
- [ ] **Step 2:** Body — classify `$ARGUMENTS` per Section A (LOC × files × audit × tenancy × auth). Bracket-bump rule: any change touching `audit_log`, `tenant_id` filters, or auth middleware is forced to Deep lane. Write `{lane, bracket, slug, audit_impact, tenancy_impact}` to `.claude/state/current-task.json`.
- [ ] **Step 3:** Lane branches:
  - **Fast** → prompt via `AskUserQuestion`: "proceed directly or create a minimal SPEC.md?" Default is proceed. If proceed, print `Fast lane: edit directly. Next: /eneo-verify`.
  - **Standard** → create `.claude/specs/<slug>/SPEC.md` (≤100 lines: Goal, Acceptance bullets, Files touched, Out of scope). Embed Stop-hook validator `validate_file_contains.py --file .claude/specs/${SLUG}/SPEC.md --contains '## Goal' --contains '## Out of scope' --max-lines 100`. Print `Standard lane: SPEC.md created. Next: /eneo-start`.
  - **Deep** → create `.claude/prds/<slug>.md` (Section B template verbatim), empty `.claude/plans/<slug>.md`, empty `.claude/phases/<slug>/`, `.claude/context/<slug>-$(date +%Y%m%dT%H%M%SZ).md` snapshot, and `gh issue create --label prd,draft --title "PRD: <slug>" --body-file .claude/prds/<slug>.md`. Embed Stop-hook validator requiring Section B template sections. Print `Deep lane: PRD + issue created. Next: /eneo-discuss`.
- [ ] **Step 4:** If the classification is borderline (bracket boundary within ±10% LOC or no clear audit/tenancy signal), use `AskUserQuestion` to confirm the lane; otherwise proceed silently.

### Task 2.2: `/eneo-discuss` — Socratic interview (Deep lane)

**Files:**
- Create: `plugins/eneo-core/commands/eneo-discuss.md`

- [ ] **Step 1:** Frontmatter — `description: Plan-mode Socratic interview (Pocock script) with SuperClaude 90/70 confidence gate. Deep lane only.`; `allowed-tools: Read, Glob, Grep, Task`; `model: opus`.
- [ ] **Step 2:** Body — require plan mode (soft via stderr hint if not active). Run Pocock's interview script verbatim ("long detailed description of the problem", "explore the repo to verify their assertions", "considered other options", "hammer out the exact scope"). Dispatch read-only `Explore` subagent to verify assertions against repo state.
- [ ] **Step 3:** Compute confidence at the end. <70% → block with specific questions. 70–89% → present alternatives and ask for clarification. ≥90% → update PRD, print `Confidence <N>%. Next: /eneo-plan`.

### Task 2.3: `/eneo-plan` — PRD → tracer-bullet phased plan (Deep lane)

**Files:**
- Create: `plugins/eneo-core/commands/eneo-plan.md`

- [ ] **Step 1:** Frontmatter per playbook Section F excerpt verbatim (the embedded Stop-hook validator calling `validate_file_contains.py` with all four `--contains` flags: `## Phase 1: Tracer Bullet`, `## Out of scope`, `PRD:`, `Wave plan:`).
- [ ] **Step 2:** Body — produce `.claude/plans/<slug>.md` using the phase template from Section C. Phase 1 is mandatory tracer bullet (schema + service + API route + SvelteKit minimal UI + 1 integration test). Phase count 3–6 per Pocock. Spawn `planner` + `architect` subagents for wave-plan drafting.
- [ ] **Step 3:** On validation success, print `Plan saved with <N> phases. Next: /eneo-start`.

### Task 2.4: `/eneo-start` — resume work (merged from /gsd-execute-phase) + Wave orchestration

**Files:**
- Create: `plugins/eneo-core/commands/eneo-start.md`

- [ ] **Step 1:** Frontmatter — `description: Resume the current plan and run its next incomplete phase. Smart defaults; only prompts when there is real ambiguity.`; `argument-hint: [<slug>] [<phase-number> | --phase <red|green|refactor|free>]`; `allowed-tools: Read, Glob, Grep, Write, Edit, Task, Bash(git:*, uv:*, bun:*, pytest:*, pyright:*)`; `model: sonnet`.
- [ ] **Step 2:** Argument parsing and smart behavior:
  - No args + current slug present + next incomplete phase exists → resume silently, print `Resuming <slug> phase <N>.`
  - No args + multiple in-flight plans + no current slug → use `AskUserQuestion` to pick; default-highlight most-recently-modified plan.
  - No args + no in-flight plans → print `No in-flight plans. Next: /eneo-new "<description>"` and exit 0.
  - `<slug>` → resume that plan at next incomplete phase.
  - `<slug> <phase-number>` → jump to that phase.
  - `<slug> --phase <red|green|refactor|free>` → **emergency override**: write `.claude/state/phase`; print `Phase set to <value>.` This is the only way a developer manually unfreezes the TDD phase machine; hooks point here in their error messages.
- [ ] **Step 3:** Wave orchestration (when running a phase):
  - Read `.claude/phases/<slug>/phase-NN-*.md`.
  - Render the barkain ASCII wave dependency graph.
  - Flip `.claude/state/phase` to `RED`; seed `.claude/state/wave.json` with `{wave: 1, expected: <N>, done: 0}`.
  - Dispatch Wave 1 subagents in a single assistant turn via parallel `Task` calls (explicit N). **TaskOutput is forbidden.** Agents return `DONE|<artifact-path>`.
  - `wave-barrier.sh` (SubagentStop) counts completions; when `done >= expected` the command flips to `GREEN` and dispatches Wave 2 (impl-writer + domain specialists).
  - Wave 3 → `REFACTOR`; dispatch integrator + reviewer.
  - After the phase completes, mark `status: shipped` in the phase file. Print `Phase <N> complete. Next: /eneo-verify`.
- [ ] **Step 4:** Enforce "≥3 unrelated tasks + clean file boundaries" before parallel dispatch (Section H anti-over-parallelization). Serial fallback otherwise.
- [ ] **Step 5:** Reject wave plans with file-path overlap between agents in the same wave (Section H shared-file race).

### Task 2.5: `/eneo-verify` — ratchet gate + conditional adversarial review

**Files:**
- Create: `plugins/eneo-core/commands/eneo-verify.md`

- [ ] **Step 1:** Frontmatter — `description: Ratchet gate: pyright strict, pytest, coverage, mutation ≥70%, audit-completeness, tenancy smoke, conditional adversarial review on risky paths.`; `allowed-tools: Read, Glob, Grep, Bash(uv:*, bun:*), Task`; `model: sonnet`.
- [ ] **Step 2:** Body — run the 7 Section F checklist items verbatim, each wrapped in `eneo_exec`:
  1. `eneo_exec "backend" uv run pyright --strict` on changed files
  2. `eneo_exec "backend" uv run pytest` — all markers green
  3. Coverage ratchet — no regression (invoke `ratchet_check.py`)
  4. Mutation score ≥70% on changed `intric/` modules (`mutmut run` + ratchet_check)
  5. Audit-log completeness — for every mutating endpoint touched, a test asserts an audit entry
  6. Tenancy isolation smoke test
  7. Conditional adversarial review if the current task tag is `audit:schema`, `tenancy:cross`, `authz`, or LOC > 800 — spawn `autoreason-judge` + (optional) codex/gemini reviewers
- [ ] **Step 3:** Write evidence (command outputs) to `.claude/phases/<slug>/phase-NN-verify.md`. Print `Phase verified. Next: /eneo-ship` (or specific failure + fix command on failure).

### Task 2.6: `/eneo-ship` — PR creation with enforced metadata

**Files:**
- Create: `plugins/eneo-core/commands/eneo-ship.md`

- [ ] **Step 1:** Frontmatter — `description: Open a PR via gh pr create with tenancy/audit/PRD/phase metadata; Stop-hook validates required fields.`; `allowed-tools: Read, Bash(gh pr create:*, git:*)`.
- [ ] **Step 2:** Body — PR body template with `tenancy:*`, `audit:*`, `PRD: #<issue>`, `Phase: <N>`, and `## Verify evidence` section. Co-Authored-By footer. PR links to PRD issue; PRD issue is **never closed** here. Post a phase-summary comment on the PRD issue.
- [ ] **Step 3:** Embed Stop-hook validator calling `pr_metadata_check.py --pr <new-pr-number>`.
- [ ] **Step 4:** On success print `PR #<NNN> opened. Next: /eneo-start (phase <M+1>)` or `Next: wait for review` if last phase.

### Task 2.7: `/eneo-recap` — close the milestone

**Files:**
- Create: `plugins/eneo-core/commands/eneo-recap.md`

- [ ] **Step 1:** Frontmatter — `description: Close the milestone. Runs only when all phases are shipped. Writes recap, closes PRD issue, archives phases.`; `allowed-tools: Read, Write, Bash(gh issue:*, git:*), Task`.
- [ ] **Step 2:** Verify all phase files have `status: shipped`. If not, print the missing phases + `Next: /eneo-start` and exit 0.
- [ ] **Step 3:** Produce `.claude/recaps/<slug>.md` (agent-os recap convention); `gh issue close <prd-issue>` with recap link; `mv .claude/phases/<slug> .claude/archive/`. Dispatch `learning-extractor` subagent to propose skill candidates.
- [ ] **Step 4:** Print `Milestone <slug> closed. Recap at .claude/recaps/<slug>.md. Next: /eneo-new "<next-description>"`.

### Task 2.8: `/eneo-prune` — quarterly skill + recap cleanup

**Files:**
- Create: `plugins/eneo-core/commands/eneo-prune.md`

- [ ] **Step 1:** Frontmatter — `description: List skills not triggered in 90 days and recaps older than 6 months for archive decision. Never auto-deletes.`; `allowed-tools: Read, Glob, Bash(git log:*)`.
- [ ] **Step 2:** Read `.claude/stats/skill-usage.jsonl` (populated by UserPromptSubmit + SubagentStart hooks). Compare against 90-day window. List un-triggered skills. List recap files in `.claude/recaps/` older than 6 months. Print a table with `[keep|archive]` recommendations.
- [ ] **Step 3:** Print `Review the list above; run /eneo-prune --archive <name> to move items to .claude/archive/. Next: back to your work`.

### Task 2.9: `/eneo-doctor` — actionable diagnostics

**Files:**
- Create: `plugins/eneo-core/commands/eneo-doctor.md`

- [ ] **Step 1:** Frontmatter — `description: Run environment diagnostics at any time. Prints the exact command to fix every issue it detects.`; `allowed-tools: Read, Bash(docker:*, uv:*, bun:*, claude plugin list:*)`.
- [ ] **Step 2:** Body — source `lib/env.sh`; call `detect_env`; run `eneo_exec` probes for `uv --version`, `pyright --version`, `bun --version`, `pytest --version`. Check: container presence in `host-with-docker` mode, `.claude/state/current-task.json` staleness (points to missing plan?), ratchet file presence, `claude plugin list` for `eneo-core` etc.
- [ ] **Step 3:** For every detected issue print a fix row (per playbook Section F `/eneo-doctor` table — uv missing, container down, stale state file, ratchet missing, pyright outdated, plugin missing). On clean, print `All checks pass. Mode=<detected>. Next: /eneo-start` or the inferred next step.

### Task 2.10: `/finding-teach` — session learning extractor (shipped in eneo-findings, registered here for visibility)

**Files:**
- Created in Phase 5 under `plugins/eneo-findings/commands/finding-teach.md` — listed here so Phase 2 verification accounts for the full user-facing command surface.

### Task 2.11: Phase 2 verification

- [ ] 9 command files exist under `plugins/eneo-core/commands/`: eneo-new, eneo-discuss, eneo-plan, eneo-start, eneo-verify, eneo-ship, eneo-recap, eneo-prune, eneo-doctor
- [ ] `/eneo-plan.md` frontmatter matches the playbook Section F verbatim (validator flags)
- [ ] Every command has required frontmatter fields (`description`, where applicable `argument-hint`, `allowed-tools`, `model`)
- [ ] `/eneo-discuss` soft-requires plan mode, `/eneo-start` has parallel-dispatch guardrail, `/eneo-new` branches on lane with the Fast-lane AskUserQuestion prompt
- [ ] Every successful command prints a `Next:` line inferred from state
- [ ] Every user-facing error from a hook references a specific `/eneo-start --phase` or `/eneo-doctor` fix command

**Commit point:** "Phase 2: eneo-core slash commands (/eneo-new, /eneo-discuss, /eneo-plan, /eneo-start, /eneo-verify, /eneo-ship, /eneo-recap, /eneo-prune, /eneo-doctor) with DX conventions"

---

## Phase 3: Subagents (eneo-core)

**Goal:** Create all 10 subagents from Section F table plus the prompt files referenced throughout. Follow plugin-dev `agent-development` skill for frontmatter structure.

### Task 3.1: `tdd-test-writer` — Section D Mechanism 3

**Files:**
- Create: `plugins/eneo-core/agents/tdd-test-writer.md`

- [ ] **Step 1:** Frontmatter and body verbatim from Section D Mechanism 3 (RED phase, receives PRD section + acceptance criteria only, writes failing integration test, confirms test fails with meaningful assertion, returns `RED: <test_path> — failing as expected: <assertion>`)
- [ ] **Step 2:** `tools: Read, Glob, Grep, Write, Edit, Bash(pytest:*, pnpm test:*)`; `model: sonnet`

### Task 3.2: `tdd-impl-writer` — Section D Mechanism 3

**Files:**
- Create: `plugins/eneo-core/agents/tdd-impl-writer.md`

- [ ] **Step 1:** Frontmatter and body verbatim from Section D (GREEN phase, reads failing test path, edits intric/ source only, smallest impl to pass test, runs pyright --strict with zero errors, returns `GREEN: <impl files> — <test> passing`)
- [ ] **Step 2:** `tools: Read, Glob, Grep, Edit, Bash(pytest:*, pyright:*, ruff:*)`; `model: sonnet`

### Task 3.3: `fastapi-specialist`

**Files:**
- Create: `plugins/eneo-core/agents/fastapi-specialist.md`

- [ ] **Step 1:** Frontmatter — pushy description: "Use for any FastAPI endpoint work in backend/src/intric/api/**. Enforces: tenant_id filter on every query, audit entry on every mutating endpoint, Pydantic v2 response models, no raw SQL."
- [ ] **Step 2:** Body — references `skills/fastapi-conventions` and `skills/audit-log-writer`; workflow: read endpoint requirement → stub router → Pydantic schemas → service → call audit-log writer → integration test.

### Task 3.4: `sveltekit-specialist`

**Files:**
- Create: `plugins/eneo-core/agents/sveltekit-specialist.md`

- [ ] **Step 1:** Pushy description: "Use for SvelteKit routes in frontend/apps/web/src/routes/**. Typed load functions, Swedish-language labels, a11y-compliant forms, no client-side secrets."
- [ ] **Step 2:** Body — references `skills/sveltekit-load-patterns`; workflow: route → +page.server.ts (typed load) → +page.svelte → minimal Playwright test.

### Task 3.5: `alembic-migrator`

**Files:**
- Create: `plugins/eneo-core/agents/alembic-migrator.md`

- [ ] **Step 1:** Pushy description: "Use for any DB schema change in backend/alembic/**. Always writes reversible migrations and tests both up and down."
- [ ] **Step 2:** Body — workflow: alembic revision → edit → `eneo_exec "backend" uv run alembic upgrade head` → test; `alembic downgrade -1` → test; commit with `alembic:` prefix.

### Task 3.6: `security-reviewer` — Section E high-ROI

**Files:**
- Create: `plugins/eneo-core/agents/security-reviewer.md`

- [ ] **Step 1:** Pushy description: "Mandatory review for any auth/permissions/tenancy/secrets change. Fresh context. Checks: authz decorators on endpoints, tenant_id filtering on all queries, no PII in logs, no secrets in code."
- [ ] **Step 2:** Body — checklist-driven; "do nothing" is a valid outcome (per autoreason Section E); return either `PASS` or a bulleted list of concrete issues with file:line references.

### Task 3.7: `audit-auditor`

**Files:**
- Create: `plugins/eneo-core/agents/audit-auditor.md`

- [ ] **Step 1:** Pushy description: "Use after any FastAPI endpoint touched. Asserts every `@router.post|put|delete|patch` has an accompanying audit-log entry and a test that verifies it."
- [ ] **Step 2:** Body — grep mutating endpoints in changed files; for each, verify `audit_log.create(...)` call path and a test assertion; emit missing-coverage list.

### Task 3.8: `tenancy-checker`

**Files:**
- Create: `plugins/eneo-core/agents/tenancy-checker.md`

- [ ] **Step 1:** Pushy description: "Enforces tenant_id filtering invariant. Checks every SQLAlchemy query path for tenant scoping via get_current_tenant()."
- [ ] **Step 2:** Body — grep `select(`, `session.query(`, `.filter(` in changed files; cross-check for tenant scoping; return violations.

### Task 3.9: `learning-extractor` — Section G

**Files:**
- Create: `plugins/eneo-core/agents/learning-extractor.md`

- [ ] **Step 1:** Pushy description: "Transcript miner. Reads session transcript, proposes a candidate skill with pushy description and 200–400 line body. Output is a draft SKILL.md + evals.md."
- [ ] **Step 2:** Body — Anthropic transcript-mining pattern; "if all 3 test cases produced the same script, bundle it"; require ≥3-query eval file (2 should-trigger + 1 near-miss).

### Task 3.10: `autoreason-judge` — Section E tournament

**Files:**
- Create: `plugins/eneo-core/agents/autoreason-judge.md`

- [ ] **Step 1:** Pushy description: "Tournament judge for A/B/AB comparisons on risky changes. Fresh context. Uses blind Borda count. 'Do nothing' is a first-class option."
- [ ] **Step 2:** Body — receives three labeled diffs (A=incumbent, B=adversarial, AB=synthesis). Ranks them 1–3 via Borda. Stops the tournament on two consecutive no-change rounds. Explicitly instructs the judge to prefer "no change" when differences are stylistic.

### Task 3.11: Phase 3 verification

- [ ] All 10 agent files exist; each has frontmatter with `name`, `description`, `tools`, `model`.
- [ ] tdd-test-writer + tdd-impl-writer match Section D verbatim
- [ ] autoreason-judge has "do nothing" first-class per Section E

**Commit point:** "Phase 3: eneo-core subagents (TDD pair, domain specialists, reviewers, learning-extractor, autoreason-judge)"

---

## Phase 4: Skills (eneo-core)

**Goal:** Create 7 new skills plus migrate `frontend-design` from top-level plugin into eneo-core. Use skills-best-practices + skill-creator patterns.

### Task 4.1: `write-prd-eneo/SKILL.md` — Section B template

**Files:**
- Create: `plugins/eneo-core/skills/write-prd-eneo/SKILL.md`

- [ ] **Step 1:** Pushy description triggering on "write PRD", "draft PRD", "new feature spec". Full Section B template (Problem/Proposed solution/Success criteria/User stories/Acceptance criteria/Module sketch/Testing decisions/Non-functional/Out of scope/Polishing/Open questions) with BAD/GOOD diff rule from awesome-copilot.
- [ ] **Step 2:** Eneo-specific adaptations: force `tenancy_impact` + `audit_impact` in frontmatter; require Swedish-language UX + a11y story when SvelteKit touched; forbid file paths in Module sketch (Pocock rule).

### Task 4.2: `prd-to-plan-eneo/SKILL.md` — Section C Pocock vertical-slice

**Files:**
- Create: `plugins/eneo-core/skills/prd-to-plan-eneo/SKILL.md`

- [ ] **Step 1:** Pushy description: "Use when a PRD is approved and needs decomposition into tracer-bullet phases." Embed Pocock's vertical-slice quote verbatim.
- [ ] **Step 2:** Phase template from Section C (Wave plan, Deliverables, Done when, Mutation-score floor). Eneo tracer-bullet definition: schema + service + API route + SvelteKit minimal UI + 1 integration test.

### Task 4.3: `prd-to-issues-eneo/SKILL.md` — Section C HITL/AFK

**Files:**
- Create: `plugins/eneo-core/skills/prd-to-issues-eneo/SKILL.md`

- [ ] **Step 1:** Pushy description: "Use after plan is drafted to produce AFK/HITL-tagged GitHub issues in dependency order."
- [ ] **Step 2:** Rules: each issue is a thin vertical slice; HITL if tenancy-model or audit-schema change, AFK otherwise; prefer AFK; `Blocked by: #<real-issue-number>` mandatory; tenancy-risk tag + audit-tag on every issue; PRD issue is never closed.

### Task 4.4: `fastapi-conventions/SKILL.md`

**Files:**
- Create: `plugins/eneo-core/skills/fastapi-conventions/SKILL.md`

- [ ] **Step 1:** Pushy description: "Use when writing or reviewing any backend/src/intric/api/** endpoint. Enforces: tenant scoping, audit entries, Pydantic v2 models, no raw SQL, SQLAlchemy 2.0 style."
- [ ] **Step 2:** Sections: routing conventions, dependency injection (`get_current_tenant`), response models, pagination, error handling with structured logging.

### Task 4.5: `pydantic-v2-patterns/SKILL.md`

**Files:**
- Create: `plugins/eneo-core/skills/pydantic-v2-patterns/SKILL.md`

- [ ] **Step 1:** Pushy description: "Use when creating or modifying Pydantic models in backend/src/intric/models/**."
- [ ] **Step 2:** Sections: `model_config` vs inner `Config`, `Field` with discriminators, `@field_validator` over root_validator, `RootModel` where appropriate, `TypeAdapter` for one-off parsing.

### Task 4.6: `sveltekit-load-patterns/SKILL.md`

**Files:**
- Create: `plugins/eneo-core/skills/sveltekit-load-patterns/SKILL.md`

- [ ] **Step 1:** Pushy description: "Use when creating SvelteKit routes in frontend/apps/web/src/routes/**."
- [ ] **Step 2:** Sections: `+page.server.ts` typed load, `PageServerLoad` types, form actions, locals.session, Swedish-language labels, a11y (aria-*, keyboard nav), no client-side secrets.

### Task 4.7: `audit-log-writer/SKILL.md`

**Files:**
- Create: `plugins/eneo-core/skills/audit-log-writer/SKILL.md`

- [ ] **Step 1:** Pushy description: "Use for every mutating endpoint touched. Writes audit entry + test assertion."
- [ ] **Step 2:** Template patterns: `audit_log.create(action=..., actor=..., resource=..., tenant_id=..., metadata=...)`; test example asserting `audit_log` table row exists after a POST/PUT/DELETE.

### Task 4.8: Move `frontend-design` into eneo-core

**Files:**
- Copy: `plugins/frontend-design/skills/frontend-design/SKILL.md` → `plugins/eneo-core/skills/frontend-design/SKILL.md`
- (Do not delete top-level `plugins/frontend-design/` yet — Phase 8)

- [ ] **Step 1:** `cp -r plugins/frontend-design/skills/frontend-design plugins/eneo-core/skills/frontend-design`
- [ ] **Step 2:** Verify SKILL.md is identical post-copy.

### Task 4.9: Phase 4 verification

- [ ] 8 skill directories under `plugins/eneo-core/skills/` (7 new + frontend-design)
- [ ] Every SKILL.md has frontmatter `name`, `description`, and optional supporting files
- [ ] Descriptions use "pushy" language (Anthropic recommendation, Section G)

**Commit point:** "Phase 4: eneo-core skills (PRD/plan/issues + FastAPI/Pydantic/SvelteKit/audit + moved frontend-design)"

---

## Phase 5: Findings plugin (eneo-findings)

**Goal:** Absorb the current `finding` plugin, extract Sundsvall-specific values to `.claude/config/findings.json` (Decision 0.3 C3), add `/finding-teach` command (Section G).

### Task 5.1: Port finding skill into eneo-findings

**Files:**
- Read: `plugins/finding/skills/finding/SKILL.md`
- Create: `plugins/eneo-findings/skills/finding/SKILL.md`

- [ ] **Step 1:** Copy the existing SKILL.md, then refactor to read config from `.claude/config/findings.json` (fields: `github_repo`, `project_number`, `project_id`, `status_field_id`, `status_options`, `labels`, `language`).
- [ ] **Step 2:** Any Sundsvall-specific literal left in text gets a `<!-- PRIVATE-OVERLAY-CANDIDATE -->` HTML comment (Decision 0.3 C3).

### Task 5.2: `/finding-teach` — Section G

**Files:**
- Create: `plugins/eneo-findings/commands/finding-teach.md`

- [ ] **Step 1:** Frontmatter — `description: Extract a candidate skill from the current transcript. Invokes learning-extractor; writes draft SKILL.md + evals.md; requires ≥3-query eval.`
- [ ] **Step 2:** Body per Section G steps 1–5 verbatim (read transcript, learning-extractor fresh context, write draft, require evals, commit on branch).

### Task 5.3: Create template `.claude/config/findings.json` (for Eneo repo)

**Files:**
- Create: `docs/eneo-repo-baseline/config/findings.json`

- [ ] **Step 1:** Copy the JSON from Decision 0.3 C3 verbatim (with `eneo-ai/eneo`, project 1, status field IDs, labels, language `sv`). This template will be copied into Eneo repo's `.claude/config/` by the user later.

### Task 5.4: Phase 5 verification

- [ ] `eneo-findings` has skill + command
- [ ] findings.json template exists under `docs/eneo-repo-baseline/config/`
- [ ] No Sundsvall hardcoded IDs remain in SKILL.md

**Commit point:** "Phase 5: eneo-findings plugin (finding skill + /finding-teach + config template)"

---

## Phase 6: Review plugin (eneo-review)

**Goal:** Absorb codex-review + gemini-review, mark trigger-gated (Section E: only on Deep-lane + risky paths).

### Task 6.1: Port codex-reviewer

**Files:**
- Read: `plugins/codex-review/skills/codex-review/SKILL.md`, `plugins/codex-review/skills/codex-review/references/eneo-context.md`
- Create: `plugins/eneo-review/agents/codex-reviewer.md`

- [ ] **Step 1:** Rewrite as a subagent prompt (not a user-invoked skill). Trigger description: "Invoked by `/eneo-verify` only when change is tagged `audit:schema`, `tenancy:cross`, `authz`, or LOC > 800." Fresh context required.
- [ ] **Step 2:** Keep the four personas (Solution Architect, API Consumer, Security Reviewer, Performance Analyst) and the `codex` CLI invocation pattern. Port eneo-context reference inline.
- [ ] **Step 3:** Output is A/B/AB compatible — ranked Borda-style per Section E.

### Task 6.2: Port gemini-reviewer

**Files:**
- Read: `plugins/gemini-review/skills/gemini-review/SKILL.md`, `plugins/gemini-review/skills/gemini-review/references/eneo-context.md`
- Create: `plugins/eneo-review/agents/gemini-reviewer.md`

- [ ] **Step 1:** Same structure as codex-reviewer; Gemini CLI; third perspective per Section E `Claude → Codex → Gemini` pipeline — but trigger-gated, not always-on.

### Task 6.3: Phase 6 verification

- [ ] Both agents exist; both explicitly state trigger conditions
- [ ] Neither is "always-on"; both feed A/B/AB tournament

**Commit point:** "Phase 6: eneo-review plugin (codex + gemini as trigger-gated review subagents)"

---

## Phase 7: Documentation

**Goal:** Produce MIGRATION.md, FUTURE_PRIVATE_OVERLAY.md, Eneo repo baseline templates, and update README.

### Task 7.0: `docs/STATE_SCHEMA.md`

**Files:**
- Create: `docs/STATE_SCHEMA.md`

- [ ] **Step 1:** Document `.claude/state/current-task.json` schema with every field, its type, writer, and readers (per playbook Section F "current-task.json schema (the DX source of truth)").
- [ ] **Step 2:** Document `.claude/state/phase` mirror file (single-word RED|GREEN|REFACTOR|FREE) and the atomicity contract (JSON updated first, mirror second).
- [ ] **Step 3:** Document write invariants: only `/eneo-new` creates; only `/eneo-recap` deletes; every writer uses `mktemp + mv`; every writer updates `last_update`; every reader uses `jq -e` with safe default.

### Task 7.1: `docs/MIGRATION.md`

**Files:**
- Create: `docs/MIGRATION.md`

- [ ] **Step 1:** Cover playbook "Migration order" items 1–11 as a developer-facing guide. Include: what changed, what to uninstall (old plugins), new slash commands list, `ENEO_DEVCONTAINER_MODE` env var, dual-mode testing.
- [ ] **Step 2:** For each old plugin, show the "absorbed into"/"deleted" disposition + migration steps.

### Task 7.2: `docs/FUTURE_PRIVATE_OVERLAY.md` — Decision 0.3

**Files:**
- Create: `docs/FUTURE_PRIVATE_OVERLAY.md`

- [ ] **Step 1:** Cover stackable marketplaces (C1), rule IDs + priorities (C2), `.claude/config/*.json` extraction (C3), and explicit list of what does NOT ship in v1.
- [ ] **Step 2:** List every `PRIVATE-OVERLAY-CANDIDATE` comment in the codebase as extraction points for future overlay.

### Task 7.3: Eneo repo baseline templates

**Files:**
- Create: `docs/eneo-repo-baseline/CLAUDE.md` — verbatim from playbook section "CLAUDE.md" (hard-capped ~80 lines)
- Create: `docs/eneo-repo-baseline/settings.json` — verbatim from playbook "Hook registration" excerpt
- Create: `docs/eneo-repo-baseline/bootstrap.md` — Decision 0.1 bootstrap flow step 3 wording
- Create: `docs/eneo-repo-baseline/rules/eneo-context.md` — Section G content (Karpathy principles with paired hook column, invariants, forbidden patterns, `@` imports)
- Create: `docs/eneo-repo-baseline/rules/fastapi-endpoints.md` — frontmatter `paths: ["backend/src/intric/api/**"]`
- Create: `docs/eneo-repo-baseline/rules/pydantic-models.md` — `paths: ["backend/src/intric/models/**"]`
- Create: `docs/eneo-repo-baseline/rules/sveltekit-routes.md` — `paths: ["frontend/apps/web/src/routes/**"]`
- Create: `docs/eneo-repo-baseline/rules/alembic-migrations.md` — `paths: ["backend/alembic/**"]`
- Create: `docs/eneo-repo-baseline/rules/audit-log.md` — `paths: ["backend/src/intric/audit/**"]`
- Create: `docs/eneo-repo-baseline/devcontainer/post-create.sh` — verbatim from Decision 0.2 seeding script

- [ ] **Step 1:** Write each file with content specified in the playbook
- [ ] **Step 2:** Each rule file includes `id:` and `priority:` frontmatter (Decision 0.3 C2)

### Task 7.4: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1:** Replace the plugin list with the four new plugins (eneo-core, eneo-standards, eneo-review, eneo-findings). Preserve the marketplace-add-path (`/plugin marketplace add CCimen/eneoplugin` is staying local so document it as such).
- [ ] **Step 2:** Add a "Migration from v1 (7 plugins) to v2 (4 plugins)" section linking to `docs/MIGRATION.md`.
- [ ] **Step 3:** Add a "Devcontainer dual-mode" note explaining `ENEO_DEVCONTAINER_MODE`.

### Task 7.5: Update marketplace.json to final state

**Files:**
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1:** Remove old plugin entries (karpathy-guidelines, vikunja-kanban, checker, codex-review, gemini-review, finding, frontend-design top-level).
- [ ] **Step 2:** Keep only the four new plugins.
- [ ] **Note:** Only run this task AFTER Phase 8 confirms removal; or alternatively, treat as the *first* step of Phase 8.

### Task 7.6: Update Eneo repo `settings.json` template with opt-in status line

**Files:**
- Modify: `docs/eneo-repo-baseline/settings.json`

- [ ] **Step 1:** Include the Section F "Hook registration" excerpt verbatim (hooks + permissions + extraKnownMarketplaces).
- [ ] **Step 2:** Add a commented-out `statusLine` example pointing at `${CLAUDE_PLUGIN_ROOT}/statusline/eneo-statusline.sh` so developers can copy-paste to opt in.

### Task 7.7: Phase 7 verification

- [ ] All documentation files exist with playbook-sourced content
- [ ] `docs/STATE_SCHEMA.md` documents every field and invariant
- [ ] README reflects the new four-plugin story + status-line opt-in mock-test
- [ ] `docs/eneo-repo-baseline/` contains every file a new Eneo clone would need

**Commit point:** "Phase 7: documentation (STATE_SCHEMA, MIGRATION, FUTURE_PRIVATE_OVERLAY, Eneo baseline templates, README)"

---

## Phase 8: Migration — destructive (REQUIRES USER APPROVAL)

**Goal:** Remove old plugin directories now that the replacements are in place. User must explicitly approve each deletion.

### Task 8.1: User checkpoint

- [ ] Pause and ask user to verify the four new plugins load correctly in Claude Code (`/plugin list`, invoke `/eneo-start`, `/eneo-doctor`).
- [ ] Only proceed after explicit user confirmation.

### Task 8.2: Delete `karpathy-guidelines`

- [ ] `rm -rf plugins/karpathy-guidelines/` — principles now live in `docs/eneo-repo-baseline/rules/eneo-context.md` paired with enforcement hooks (Section G).

### Task 8.3: Delete `vikunja-kanban`

- [ ] `rm -rf plugins/vikunja-kanban/` — GitHub Projects is sole source of truth (Decision 0.1, Section H two-kanban remedy).

### Task 8.4: Delete old `checker` (absorbed into eneo-standards)

- [ ] Verify `plugins/eneo-standards/hooks/typecheck-stop.py` is functional via `/eneo-doctor`.
- [ ] `rm -rf plugins/checker/`.

### Task 8.5: Delete old `finding` (absorbed into eneo-findings)

- [ ] Verify `/finding` still works via eneo-findings.
- [ ] `rm -rf plugins/finding/`.

### Task 8.6: Delete old `codex-review` and `gemini-review`

- [ ] Verify review subagents invokable from `/eneo-verify`.
- [ ] `rm -rf plugins/codex-review/ plugins/gemini-review/`.

### Task 8.7: Delete top-level `frontend-design` (moved into eneo-core)

- [ ] Verify `/frontend-design` still triggers via `plugins/eneo-core/skills/frontend-design/`.
- [ ] `rm -rf plugins/frontend-design/`.

### Task 8.8: Finalize marketplace.json (if not already done in 7.5)

- [ ] Apply Task 7.5 changes.

### Task 8.9: Phase 8 verification

- [ ] `ls plugins/` returns exactly 4 directories: eneo-core, eneo-standards, eneo-review, eneo-findings
- [ ] `marketplace.json` lists exactly 4 plugins
- [ ] Every slash command from Section F invokable
- [ ] `/eneo-doctor` reports correct mode and tool versions

**Commit point:** "Phase 8: migrate — remove 7 old plugins replaced by 4-plugin structure"

---

## Self-Review

### Spec-coverage cross-check (playbook → plan)

| Playbook section | Covered by |
|---|---|
| 0.1 Hybrid repo strategy | Plan scope note + docs/eneo-repo-baseline (7.3) + marketplace.json (0.7/7.5) |
| 0.2 Devcontainer dual-mode | env.sh (0.5) + env.py (0.6) + /eneo-doctor (2.11) |
| 0.3 Private-overlay stub | FUTURE_PRIVATE_OVERLAY.md (7.2) + findings.json (5.3) + rule frontmatter (7.3) |
| A Bracket/lane framing | /eneo-start (2.1) |
| B PRD template | /eneo-milestone (2.3) + write-prd-eneo skill (4.1) |
| C PRD→plan→issues | /eneo-plan (2.5) + prd-to-plan-eneo (4.2) + prd-to-issues-eneo (4.3) |
| D.1 phase-gate hook | Task 1.1 |
| D.2 bash-firewall hook | Task 1.2 |
| D.3 subagent isolation | tdd-test-writer (3.1) + tdd-impl-writer (3.2) |
| D.4 dual ratchets | stop-ratchet.sh (1.8) + trivial_test_detector (1.13) + /eneo-verify (2.7) |
| D.5 staged commits | Documented in MIGRATION.md (7.1); enforcement via future pre-commit hook (stub noted) |
| E Review cadence | /eneo-verify conditional trigger (2.7) + autoreason-judge (3.10) + eneo-review plugin (Phase 6) |
| F.1 /eneo-start | Task 2.1 |
| F.2 /eneo-spec | Task 2.2 |
| F.3 /eneo-milestone | Task 2.3 |
| F.4 /eneo-discuss | Task 2.4 |
| F.5 /eneo-plan | Task 2.5 |
| F.6 /eneo-execute | Task 2.6 |
| F.7 /eneo-verify | Task 2.7 |
| F.8 /eneo-ship | Task 2.8 |
| F.9 /eneo-recap | Task 2.9 |
| F.10 /eneo-prune | Task 2.10 |
| F.11 /eneo-doctor | Task 2.11 |
| G /finding-teach + eneo-context + pruning | 5.2 + 7.3 rules/eneo-context.md + 2.10 |
| H Anti-pattern catalog | Each remedy mapped to its task; catalog quoted in MIGRATION.md |
| Recommended workflow CLAUDE.md | 7.3 |
| Hook registration settings.json | 7.3 |
| Migration order (11 steps) | Steps mapped to phases 0→8; step 7 (Eneo repo baseline) delivered as templates in 7.3 |

### Placeholder scan

- No "TBD" steps — each task references either an exact playbook section or explicit code content
- No "add error handling" without specifics — hooks call out exact conditions (e.g., GREEN + test path match)
- No "similar to Task N" references — content is spelled out or cited by section

### Type consistency

- `eneo_exec <workdir> <cmd> [args...]` used consistently across all hooks, commands, and skills
- Phase values (`RED`, `GREEN`, `REFACTOR`, `FREE`) consistent across phase-gate, bash-firewall, /eneo-execute
- Tag vocabulary (`tenancy:*`, `audit:*`) consistent across /eneo-start, /eneo-ship, pr_metadata_check.py
- PRD template section headers consistent across /eneo-milestone validator flags and write-prd-eneo SKILL.md

### Open questions

- **Plan-mode entry detection:** `/eneo-discuss` "requires plan mode" — enforcement currently documented via hook stderr; if stricter enforcement is needed, Phase 2 can add a `validate_plan_mode.py` validator. Marked as future hardening in MIGRATION.md.
- **Staged-commits pre-commit hook (Section D Mechanism 5):** Documented but not implemented in this pass. Tasked for a follow-up commit after Phase 8 since it requires coordination with Eneo repo's existing commit hooks.
- **ratchet files initial state:** `.claude/ratchet/coverage.json` and `mutation.json` must exist on first run; stop-ratchet.sh treats missing files as "no baseline yet" (soft-pass first run, write on success).
