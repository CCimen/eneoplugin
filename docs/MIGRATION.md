# Migration guide — `eneoplugin` v1 → `eneo-agent-harness` v2

**v1** shipped seven independent plugins. **v2** consolidates them into **four** plugins with hook-enforced standards, a `/eneo-*` slash-command lineup, and a dual-mode devcontainer integration. The playbook (`eneo-harness-playbook.md`) is the design spec; this doc is the developer-facing migration walkthrough.

## What changed

| v1 plugin | Disposition |
|---|---|
| `karpathy-guidelines` | **Deleted.** Principles moved into `.claude/rules/eneo-context.md` paired one-to-one with enforcement hooks (see Section G of the playbook). |
| `vikunja-kanban` | **Deleted.** GitHub Projects is the sole source of truth (Decision 0.1, Section H two-kanban remedy). |
| `checker` | **Absorbed into `eneo-standards`.** `find_repo_root()` ported to `plugins/eneo-standards/hooks/lib/env.sh`; `typecheck-stop.py` ported to `plugins/eneo-standards/hooks/typecheck-stop.py`. |
| `finding` | **Absorbed into `eneo-findings`.** IDs extracted to `.claude/config/findings.json`. |
| `codex-review` | **Absorbed into `eneo-review`** as a trigger-gated subagent. No longer always-on. |
| `gemini-review` | **Absorbed into `eneo-review`** as a trigger-gated subagent. |
| `frontend-design` | **Moved into `eneo-core/skills/frontend-design/`.** |

## New plugin layout

```
plugins/
├── eneo-core/        # slash commands, subagents, skills
├── eneo-standards/   # hooks + validators + status line
├── eneo-review/      # trigger-gated external reviewers (codex + gemini)
└── eneo-findings/    # GitHub Projects skill + /finding-teach
```

## New command lineup

| Command | Purpose |
|---|---|
| `/eneo-new <description>` | Triage + create artifact (Fast/Standard/Deep lane) |
| `/eneo-discuss` | Socratic interview + 90/70 confidence gate (Deep lane) |
| `/eneo-plan` | PRD → tracer-bullet phased plan (Deep lane) |
| `/eneo-start [<slug>] [<phase>\|--phase <state>]` | Resume work, run wave, or emergency phase override |
| `/eneo-verify` | Ratchet gate (pyright / pytest / coverage / mutation / audit / tenancy) + conditional adversarial review |
| `/eneo-ship` | `gh pr create` with enforced metadata |
| `/eneo-recap` | Close milestone, write milestone recap, archive phases |
| `/eneo-doctor` | Runnable any time; prints exact fix for every detected issue |
| `/eneo-prune` | Quarterly skill + recap cleanup (never auto-deletes) |
| `/finding-teach <name>` | Extract a session pattern into a candidate skill |

Discovery note: Claude Code's `/help` is mostly the built-in command list. To discover namespaced plugin commands, type `/` and filter by `eneo`, or inspect the plugin in `/plugin`.

Three lanes, three happy paths:

- **Fast:** `/eneo-new` (choose "proceed") → edit → `/eneo-verify` → `/eneo-ship`
- **Standard:** `/eneo-new` → `/eneo-start` → `/eneo-verify` → `/eneo-ship`
- **Deep:** `/eneo-new` → `/eneo-discuss` → `/eneo-plan` → `/eneo-start` (per phase) → `/eneo-verify` → `/eneo-ship` → `/eneo-recap`

## Upgrade checklist (per developer)

1. **Install v2 plugins.** From any Eneo clone with the marketplace configured:
   ```
   /plugin install eneo-core@eneo-agent-harness
   /plugin install eneo-standards@eneo-agent-harness
   /plugin install eneo-findings@eneo-agent-harness
   /plugin install eneo-review@eneo-agent-harness   # optional
   ```
2. **Uninstall v1 plugins.**
   ```
   /plugin uninstall karpathy-guidelines@eneoplugin
   /plugin uninstall vikunja-kanban@eneoplugin
   /plugin uninstall checker@eneoplugin
   /plugin uninstall finding@eneoplugin
   /plugin uninstall codex-review@eneoplugin
   /plugin uninstall gemini-review@eneoplugin
   /plugin uninstall frontend-design@eneoplugin
   ```
3. **Copy the Eneo repo baseline.** From `docs/eneo-repo-baseline/` in the harness, copy the files into your Eneo clone's `.claude/` directory. The files that must be applied:
   - `CLAUDE.md` (≤80 lines; imports eneo-context.md)
   - `settings.json` (hooks + permissions + marketplace)
   - `rules/eneo-context.md` + all path-scoped rule files
   - `bootstrap.md`
   - `config/findings.json` — edit project IDs for your municipality
4. **Update your devcontainer.** Append the `post-create.sh` additions from `docs/eneo-repo-baseline/devcontainer/post-create.sh`.
5. **Mark hook scripts executable.** After cloning the harness into the marketplace cache, run once:
   ```
   chmod +x plugins/eneo-standards/hooks/*.sh \
            plugins/eneo-standards/hooks/*.py \
            plugins/eneo-standards/hooks/validators/*.py \
            plugins/eneo-standards/bin/* \
            plugins/eneo-standards/hooks/lib/env.sh \
            plugins/eneo-standards/statusline/eneo-statusline.sh
   ```
   (Git tracks the mode bit but some clone mechanisms strip it.)
6. **Run `/eneo-doctor`.** It prints a one-line fix for anything still misconfigured.

## Dual-mode environment (`ENEO_DEVCONTAINER_MODE`)

Hooks auto-detect where tools live. Override with:

| Value | Meaning |
|---|---|
| `in-container` | Claude Code attached directly to the devcontainer |
| `host-with-docker` | Claude Code on the host; `eneo_exec` uses `docker exec` |
| `native` | Host with tools installed locally (rare) |
| `disabled` | Skip `eneo_exec` wrappers (diagnostic) |

`/eneo-doctor` prints the detected mode and the right env var to set for override.

## Status line (opt-in)

Add to your `.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "${CLAUDE_PLUGIN_ROOT}/statusline/eneo-statusline.sh",
    "refreshInterval": 2
  }
}
```

Two lines: session context + harness state (`<slug> · Phase 2/3 · Wave 2/3 [▓▓▓░░] · GREEN · 🔨 active-agents`). The default view prioritizes context %, git/worktree state, rate-limit pressure, and duration; cost is opt-in via `ENEO_STATUSLINE_SHOW_COST=1`. `refreshInterval: 2` keeps the status line fresh while the coordinator waits on background subagents and no main-session event is firing.

## Permissions tuning

The baseline `settings.json` template ships with an initial `permissions.allow` list for common safe harness commands (`uv run pyright`, `uv run pytest`, `uv run mutmut`, `bun run check/test`, `jq`, read-only git/gh flows, and the equivalent `docker exec ...` variants for host-with-docker mode). Keep side-effectful commands such as `git push`, `gh pr create`, `gh pr merge`, and `gh issue create` in `ask`.

After the first few real sessions, run `/fewer-permission-prompts` to tighten the allowlist from actual history. That gives you empirical tuning without broad speculative allow rules.

## `.claude/` ignore strategy

Many existing Eneo clones still ignore `.claude/` wholesale. Keep that during local rollout if you only want local state and settings, because it prevents runtime artifacts such as `.claude/state/`, `.claude/stats/`, and temporary worktree metadata from polluting Git.

When you're ready to adopt a committed shared baseline, replace the blanket `.claude/` ignore with selective ignores. At that point, keep ignoring runtime-only paths like:

- `.claude/state/`
- `.claude/stats/`
- `.claude/worktrees/`
- `.claude/.scc-marketplaces/`
- `.claude/.scc-managed.json`
- `.claude/*.local.json`

Do that as a deliberate baseline-adoption change, not during early plugin smoke testing.

## Session recaps vs milestone recaps

Claude Code's built-in `/recap` is a session summary for resuming work after time away. `/eneo-recap` is the harness command for closing a milestone and writing `.claude/recaps/<slug>.md`. Keep `session-start-context.sh` to a one-line resume hint; let the native recap feature handle the longer conversational summary.

## Why we are not adding beads / `br` to the core harness

The harness already has three distinct layers with clear roles:

- `.claude/state/current-task.json` for live per-session flow state
- `.claude/phases/` and `.claude/recaps/` for authored artifacts
- GitHub issues / findings for shared backlog and review work

Adding beads/`br` on top of that would create another state system to reconcile. During rollout, that is more likely to hurt developer experience than help it. If the team later wants a local-first backlog tool, treat `br` as an optional companion workflow rather than a required harness dependency.

Test with the mock-input command:

```sh
echo '{"model":{"display_name":"Opus 4.7"},"workspace":{"current_dir":"/eneo"},"context_window":{"used_percentage":42},"cost":{"total_cost_usd":0.18,"total_duration_ms":720000},"session_id":"test"}' \
  | plugins/eneo-standards/statusline/eneo-statusline.sh
```

## New hook events

The `eneo-standards` plugin registers:

| Event | Hook | Purpose |
|---|---|---|
| `SessionStart` | `session-start-bootstrap.sh` | Print install hints if harness missing |
| `SessionStart` | `session-start-context.sh` | Print current slug + phase on open |
| `UserPromptSubmit` | `user-prompt-audit.sh` | Log to `.claude/stats/prompts.jsonl`; refresh `last_update` |
| `PreToolUse:Edit\|Write\|MultiEdit` | `phase-gate.sh` | Block test edits in GREEN / src edits in RED |
| `PreToolUse:Edit\|Write\|MultiEdit` | `protect-files.sh` | Block .env / lockfile / ratchet-file edits |
| `PreToolUse:Bash` | `bash-firewall.sh` | Block bash-based phase-gate bypass |
| `SubagentStop` | `wave-barrier.sh` | Advance wave counter; clear active agents |
| `PreCompact` | `pre-compact-snapshot.sh` | Persist wave scratchpad before compaction |
| `Stop` | `stop-ratchet.sh` | Coverage + mutation ratchet enforcement |
| `Stop` | `typecheck-stop.py` | Pyright strict (ported from v1 checker) |

Error messages from every hook follow the 3-part pattern: `what / rule / fix` — the `fix` always names a specific command or file edit.

## State schema

`.claude/state/current-task.json` is the DX source of truth; every command and every hook reads and writes via the `eneo_task_update` helper in `plugins/eneo-standards/hooks/lib/state.sh`. Full schema in `docs/STATE_SCHEMA.md`.

## Common migration gotchas

- **Old `/codex-review` and `/gemini-review` usage.** These were always-on in v1; in v2 they're gated behind risk flags. If you need ad-hoc review, run `/eneo-verify` on a throwaway branch — it will skip review on low-risk changes with an explanation.
- **Old `/karpathy-guidelines` mental model.** The four Karpathy principles (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution) are now paired with enforcement hooks. Think-before-coding is the confidence gate in `/eneo-discuss`; Simplicity is the LOC check in `/eneo-verify`; Surgical Changes is the files-list check in the pre-commit hook; Goal-Driven is every phase's `Done when:` clause.
- **Old `/finding` expecting hardcoded IDs.** Copy `docs/eneo-repo-baseline/config/findings.json` to `.claude/config/findings.json` and edit for your project. The skill reads from the config every call.
- **Old `/checker` CLAUDE.md.** The new CLAUDE.md template imports `rules/eneo-context.md` which holds the same pyright-strict invariant. Don't keep both — delete the old one.

## What didn't change

- The **Eneo pyright ratchet** baseline format (`.pyright-baseline.json`) and `typecheck_changed.sh` script. The new hook calls the same script; no CI changes needed.
- The **GitHub Projects board.** Same board, same labels, same status IDs — just read from config now.
- The **mandatory audit log on every mutation** invariant. Now enforced by the `audit-auditor` subagent and Gate 5 of `/eneo-verify`.

## Where to get help

- Playbook: `eneo-harness-playbook.md` (design spec)
- State schema: `docs/STATE_SCHEMA.md`
- Private overlay future: `docs/FUTURE_PRIVATE_OVERLAY.md`
- `/eneo-doctor` for any "something is wrong" question — it prints the fix.
