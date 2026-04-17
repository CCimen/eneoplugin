import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
sys.path.insert(0, str(REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "lib"))
import env as eneo_env  # type: ignore[import-not-found]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_fixture(name: str) -> dict:
    return read_json(FIXTURES / name)


def run_shell_script(script: Path, payload: dict, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["bash", str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=merged_env,
        check=False,
    )


def run_python_script(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        text=True,
        capture_output=True,
        cwd=str(cwd) if cwd else None,
        check=False,
    )


def run_executable(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(script), *args],
        text=True,
        capture_output=True,
        cwd=str(cwd) if cwd else None,
        check=False,
    )


class HarnessRegressionTests(unittest.TestCase):
    def test_eneo_new_fast_lane_prompt_avoids_redundant_question_for_bracket_one(self) -> None:
        command = (REPO_ROOT / "plugins" / "eneo-core" / "commands" / "eneo-new.md").read_text(encoding="utf-8")
        self.assertIn("Never ask a \"proceed or spec?\" question for an obvious Bracket 1 request", command)
        self.assertIn("inspect the most likely target files yourself", command)
        self.assertIn("Do not end with \"Where is it?\"", command)
        self.assertIn("do **not** create or refresh `current-task.json`", command)
        self.assertIn("do **not** set `next_hint` to `/eneo-verify`", command)
        self.assertIn("Before writing any state or printing any success banner", command)
        self.assertIn("If still ambiguous after inspection", command)
        self.assertIn("Do not create `.claude/state/`, `.claude/stats/`, scratch files", command)
        self.assertIn("prefer `Read`/`Grep` over shell pipelines", command)
        self.assertIn("use `eneo-task-init` / `eneo-task-update`", command)
        self.assertIn("Never emit a raw `tmp=$(mktemp)", command)
        self.assertIn("Do not print this success banner before the edit has actually happened", command)
        self.assertIn("Never print the banner before step 2", command)
        self.assertIn("Fast-lane output should stay terse", command)

    def test_env_prefers_running_eneo_app_container_name(self) -> None:
        names = [
            "eneo-41ae93-db-1",
            "eneo-41ae93-redis-1",
            "eneo-41ae93-celery-worker-flows-1",
            "eneo-41ae93-eneo-1",
        ]
        self.assertEqual(eneo_env._preferred_eneo_container(names), "eneo-41ae93-eneo-1")

    @mock.patch("env.subprocess.run")
    def test_detect_env_recognizes_host_with_docker_for_eneo_container(self, mock_run: mock.Mock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            ["docker", "ps", "--format", "{{.Names}}"],
            0,
            "eneo-41ae93-eneo-1\neneo-41ae93-db-1\n",
            "",
        )
        with mock.patch.dict(os.environ, {}, clear=False):
            self.assertEqual(eneo_env.detect_env(), "host-with-docker")

    def test_required_hook_and_bin_files_are_executable(self) -> None:
        required = [
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "bash-firewall.sh",
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "phase-gate.sh",
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "protect-files.sh",
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "session-start-bootstrap.sh",
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "session-start-context.sh",
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "stop-ratchet.sh",
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "typecheck-stop.py",
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "user-prompt-audit.sh",
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "wave-barrier.sh",
            REPO_ROOT / "plugins" / "eneo-standards" / "statusline" / "eneo-statusline.sh",
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-env-report",
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-exec",
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-phase-set",
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-ratchet-check",
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-task-init",
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-task-update",
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-doctor-report",
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-commit-preflight",
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-commit-message-check",
        ]
        for path in required:
            self.assertTrue(path.exists(), str(path))
            self.assertTrue(os.access(path, os.X_OK), f"not executable: {path}")

    def test_eneo_commit_prompt_uses_helpers_and_conditional_security_review(self) -> None:
        command = (REPO_ROOT / "plugins" / "eneo-core" / "commands" / "eneo-commit.md").read_text(encoding="utf-8")
        self.assertIn("eneo-commit-preflight --json", command)
        self.assertIn("eneo-commit-message-check --json", command)
        self.assertIn("security-reviewer", command)
        self.assertIn("Do **not** block solely on the subagent's opinion", command)
        self.assertIn("Let `git commit` run the repository's normal commit hooks", command)
        self.assertIn("Next: /eneo-ship", command)

    def test_plugin_subagents_use_plain_tool_names_and_preload_referenced_skills(self) -> None:
        agent_paths = sorted((REPO_ROOT / "plugins" / "eneo-core" / "agents").glob("*.md"))
        agent_paths += sorted((REPO_ROOT / "plugins" / "eneo-review" / "agents").glob("*.md"))
        for path in agent_paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"^tools: .*Bash\(", msg=f"patterned Bash tools in {path}")

        fastapi = (REPO_ROOT / "plugins" / "eneo-core" / "agents" / "fastapi-specialist.md").read_text(encoding="utf-8")
        self.assertRegex(fastapi, r"(?m)^skills:\n  - fastapi-conventions\n  - audit-log-writer\n  - pydantic-v2-patterns$")

        sveltekit = (REPO_ROOT / "plugins" / "eneo-core" / "agents" / "sveltekit-specialist.md").read_text(encoding="utf-8")
        self.assertRegex(sveltekit, r"(?m)^skills:\n  - sveltekit-load-patterns$")

    def make_repo_root(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="eneo-harness-tests-"))
        (root / "backend" / "src" / "intric").mkdir(parents=True)
        (root / ".claude" / "state").mkdir(parents=True)
        return root

    def init_git_repo(self, root: Path, branch: str = "feature/demo") -> None:
        subprocess.run(["git", "init", "-b", branch], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True, text=True)

    def write_task_state(self, root: Path, *, active_agents: list[str]) -> Path:
        state_path = root / ".claude" / "state" / "current-task.json"
        write_json(
            state_path,
            {
                "slug": "demo",
                "lane": "deep",
                "bracket": 4,
                "tenancy_impact": "tenant-scoped",
                "audit_impact": "appends",
                "phase": 1,
                "phase_total": 2,
                "phase_name": "demo phase",
                "tdd_phase": "GREEN",
                "wave": 1,
                "wave_total": 2,
                "wave_status": {"1": "in_progress", "2": "pending"},
                "active_agents": active_agents,
                "status": "in_progress",
                "started_at": "2026-04-16T12:30:00Z",
                "last_update": "2026-04-16T12:30:00Z",
                "next_hint": None,
                "prd_issue": 123,
                "last_pr": None,
            },
        )
        return state_path

    def test_pr_metadata_validator_accepts_ship_template(self) -> None:
        body = """## Summary
- Implemented the thing

## Metadata
- **PRD:** #123
- **Phase:** 2
- **tenancy:** tenant-scoped
- **audit:** schema
- **lane:** deep

## Verify evidence
All checks pass.

## Test plan
- [ ] Replay evidence
"""
        with tempfile.TemporaryDirectory(prefix="eneo-pr-body-") as tmp:
            body_path = Path(tmp) / "body.md"
            body_path.write_text(body, encoding="utf-8")
            result = run_python_script(
                REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "validators" / "pr_metadata_check.py",
                "--body-file",
                str(body_path),
            )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_pr_metadata_validator_rejects_missing_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="eneo-pr-body-") as tmp:
            body_path = Path(tmp) / "body.md"
            body_path.write_text("## Summary\nMissing metadata.\n", encoding="utf-8")
            result = run_python_script(
                REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "validators" / "pr_metadata_check.py",
                "--body-file",
                str(body_path),
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("missing required metadata", result.stderr)

    def test_ratchet_validator_flags_coverage_regression(self) -> None:
        root = self.make_repo_root()
        ratchet_dir = root / ".claude" / "ratchet"
        ratchet_dir.mkdir(parents=True)
        write_json(ratchet_dir / "coverage.json", {"backend/src/intric/demo.py": 80})
        write_json(ratchet_dir / "mutation.json", {})
        write_json(
            root / "coverage.json",
            {
                "files": {
                    "backend/src/intric/demo.py": {
                        "summary": {"percent_covered": 72}
                    }
                }
            },
        )

        result = run_python_script(
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "validators" / "ratchet_check.py",
            "--coverage",
            str(ratchet_dir / "coverage.json"),
            "--mutation",
            str(ratchet_dir / "mutation.json"),
            "--repo-root",
            str(root),
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("coverage regression", result.stderr)

    def test_ratchet_validator_init_bootstraps_empty_baselines(self) -> None:
        root = self.make_repo_root()
        ratchet_dir = root / ".claude" / "ratchet"

        result = run_python_script(
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "validators" / "ratchet_check.py",
            "--init",
            "--repo-root",
            str(root),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(read_json(ratchet_dir / "coverage.json"), {})
        self.assertEqual(read_json(ratchet_dir / "mutation.json"), {})

    def test_ratchet_validator_can_fail_on_missing_current_artifacts(self) -> None:
        root = self.make_repo_root()
        ratchet_dir = root / ".claude" / "ratchet"
        ratchet_dir.mkdir(parents=True)
        write_json(ratchet_dir / "coverage.json", {"backend/src/intric/demo.py": 80})
        write_json(ratchet_dir / "mutation.json", {})

        result = run_python_script(
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "validators" / "ratchet_check.py",
            "--coverage",
            str(ratchet_dir / "coverage.json"),
            "--mutation",
            str(ratchet_dir / "mutation.json"),
            "--repo-root",
            str(root),
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("artifacts are missing", result.stderr)

    def test_protect_files_blocks_direct_phase_edits(self) -> None:
        result = run_shell_script(
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "protect-files.sh",
            {"tool_input": {"file_path": "/tmp/demo/.claude/state/phase"}},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("eneo_phase_set", result.stderr)

    def test_bash_firewall_blocks_phase_file_redirects(self) -> None:
        root = self.make_repo_root()
        (root / ".claude" / "state" / "phase").write_text("GREEN\n", encoding="utf-8")

        result = run_shell_script(
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "bash-firewall.sh",
            {"tool_input": {"command": "echo GREEN > .claude/state/phase"}},
            env={"CLAUDE_PROJECT_DIR": str(root)},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("eneo_phase_set", result.stderr)

    def test_wave_barrier_counts_done_and_marks_in_progress(self) -> None:
        root = self.make_repo_root()
        write_json(
            root / ".claude" / "state" / "wave.json",
            {"wave": 1, "expected": 2, "done": 0, "status": "in-progress"},
        )
        self.write_task_state(root, active_agents=["Explore", "Plan"])

        payload = read_fixture("subagent_stop_done.json")
        payload["agent_id"] = "agent-1"
        result = run_shell_script(
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "wave-barrier.sh",
            payload,
            env={"CLAUDE_PROJECT_DIR": str(root)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1/2 (in-progress)", result.stderr)

        wave = read_json(root / ".claude" / "state" / "wave.json")
        task = read_json(root / ".claude" / "state" / "current-task.json")
        self.assertEqual(wave["done"], 1)
        self.assertEqual(wave["status"], "in-progress")
        self.assertEqual(task["wave_status"]["1"], "in_progress")
        self.assertEqual(task["active_agents"], ["Plan"])

    def test_wave_barrier_dedupes_repeated_subagent_stop(self) -> None:
        root = self.make_repo_root()
        write_json(
            root / ".claude" / "state" / "wave.json",
            {"wave": 1, "expected": 1, "done": 0, "status": "in-progress"},
        )
        self.write_task_state(root, active_agents=["Explore"])

        payload = read_fixture("subagent_stop_done.json")
        payload["agent_id"] = "agent-1"
        first = run_shell_script(
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "wave-barrier.sh",
            payload,
            env={"CLAUDE_PROJECT_DIR": str(root)},
        )
        second = run_shell_script(
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "wave-barrier.sh",
            payload,
            env={"CLAUDE_PROJECT_DIR": str(root)},
        )

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)

        wave = read_json(root / ".claude" / "state" / "wave.json")
        self.assertEqual(wave["done"], 1)

    def test_wave_barrier_ignores_blocked_subagents(self) -> None:
        root = self.make_repo_root()
        write_json(
            root / ".claude" / "state" / "wave.json",
            {"wave": 1, "expected": 1, "done": 0, "status": "in-progress"},
        )
        self.write_task_state(root, active_agents=["Explore"])

        payload = read_fixture("subagent_stop_blocked.json")
        payload["agent_id"] = "agent-2"
        result = run_shell_script(
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "wave-barrier.sh",
            payload,
            env={"CLAUDE_PROJECT_DIR": str(root)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)

        wave = read_json(root / ".claude" / "state" / "wave.json")
        task = read_json(root / ".claude" / "state" / "current-task.json")
        self.assertEqual(wave["done"], 0)
        self.assertEqual(wave["status"], "in-progress")
        self.assertEqual(task["wave_status"]["1"], "in_progress")
        self.assertEqual(task["active_agents"], [])

    def test_wave_barrier_removes_only_one_duplicate_active_agent(self) -> None:
        root = self.make_repo_root()
        write_json(
            root / ".claude" / "state" / "wave.json",
            {"wave": 1, "expected": 3, "done": 0, "status": "in-progress"},
        )
        self.write_task_state(root, active_agents=["Explore", "Explore", "Plan"])

        payload = read_fixture("subagent_stop_done.json")
        payload["agent_id"] = "agent-3"
        result = run_shell_script(
            REPO_ROOT / "plugins" / "eneo-standards" / "hooks" / "wave-barrier.sh",
            payload,
            env={"CLAUDE_PROJECT_DIR": str(root)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        task = read_json(root / ".claude" / "state" / "current-task.json")
        self.assertEqual(task["active_agents"], ["Explore", "Plan"])

    def test_commit_preflight_flags_junk_and_security_sensitive_paths(self) -> None:
        root = self.make_repo_root()
        self.init_git_repo(root, branch="spike/demo")
        (root / ".DS_Store").write_text("junk\n", encoding="utf-8")
        router = root / "backend" / "src" / "intric" / "tenant_router.py"
        router.write_text("from fastapi import APIRouter\n", encoding="utf-8")
        subprocess.run(["git", "add", ".DS_Store", str(router.relative_to(root))], cwd=root, check=True, capture_output=True, text=True)

        result = run_executable(
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-commit-preflight",
            "--json",
            "--repo-root",
            str(root),
        )

        self.assertEqual(result.returncode, 2, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn(".DS_Store: staged macOS metadata file. Remove it from the commit.", payload["hard_failures"])
        self.assertTrue(payload["signals"]["security_review_needed"])
        self.assertTrue(payload["signals"]["openapi_review_needed"])
        self.assertTrue(payload["signals"]["docs_update_likely"])
        self.assertTrue(any("does not match the preferred prefixes" in warning for warning in payload["warnings"]))

    def test_commit_message_check_rejects_placeholder_subject(self) -> None:
        result = run_executable(
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-commit-message-check",
            "--json",
            "--message",
            "WIP",
        )

        self.assertEqual(result.returncode, 2, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertTrue(any("too vague" in failure for failure in payload["hard_failures"]))

    def test_commit_message_check_warns_for_migration_prefix(self) -> None:
        root = self.make_repo_root()
        self.init_git_repo(root)
        migration = root / "backend" / "alembic" / "versions" / "1234_demo.py"
        migration.parent.mkdir(parents=True, exist_ok=True)
        migration.write_text("revision = '1234'\n", encoding="utf-8")
        subprocess.run(["git", "add", str(migration.relative_to(root))], cwd=root, check=True, capture_output=True, text=True)

        result = run_executable(
            REPO_ROOT / "plugins" / "eneo-standards" / "bin" / "eneo-commit-message-check",
            "--json",
            "--repo-root",
            str(root),
            "--message",
            "Add migration",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(any("`alembic:` subject prefix" in warning for warning in payload["warnings"]))


if __name__ == "__main__":
    unittest.main()
