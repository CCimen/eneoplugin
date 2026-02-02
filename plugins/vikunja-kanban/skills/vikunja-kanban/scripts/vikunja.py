#!/usr/bin/env python3
"""Vikunja Kanban helper.

Safe defaults:
- Never deletes tasks
- Only edits descriptions for managed tasks
- Uses comment-only updates by default
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

MANAGED_MARKER = "<!-- vikunja-skill:managed -->"
STATUS_START = "<!-- vikunja-skill:status-start -->"
STATUS_END = "<!-- vikunja-skill:status-end -->"

DEFAULT_PROJECT = "Internal TODO"
DEFAULT_VIEW = "Kanban"
DEFAULT_BUCKET = "Idé"


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)




_ZSHRC_LOADED = False


def load_zshrc_env() -> None:
    global _ZSHRC_LOADED
    if _ZSHRC_LOADED:
        return
    _ZSHRC_LOADED = True

    zshrc_path = os.path.expanduser("~/.zshrc")
    if not os.path.isfile(zshrc_path):
        return

    try:
        lines = Path(zshrc_path).read_text().splitlines()
    except OSError:
        return

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[len('export '):].strip()
        if not line.startswith('VIKUNJA_'):
            continue
        if '=' not in line:
            continue
        key, val = line.split('=', 1)
        key = key.strip()
        val = val.strip()
        if not (val.startswith('"') or val.startswith("'")) and '#' in val:
            val = val.split('#', 1)[0].rstrip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        if key and key not in os.environ:
            os.environ[key] = val


def get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if not value:
        load_zshrc_env()
        value = os.environ.get(name, default)
    if required and not value:
        die(f"Missing required env var: {name}")
    return value or ""


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def api_url(base_url: str, path: str) -> str:
    return f"{normalize_base_url(base_url)}/api/v1{path}"


def request_json(
    method: str,
    base_url: str,
    token: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Any:
    url = api_url(base_url, path)
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    if payload is not None:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        die(f"HTTP {exc.code} {exc.reason} for {url}\n{body}")
    except urllib.error.URLError as exc:
        die(f"Network error for {url}: {exc.reason}")


def list_projects(base_url: str, token: str) -> List[Dict[str, Any]]:
    return request_json("GET", base_url, token, "/projects", params={"page": 1, "per_page": 100}) or []


def find_project_id(base_url: str, token: str, name: str) -> int:
    projects = list_projects(base_url, token)
    for proj in projects:
        if proj.get("title", "").strip().lower() == name.strip().lower():
            return int(proj["id"])
    die(f"Project not found: {name}")


def list_views(base_url: str, token: str, project_id: int) -> List[Dict[str, Any]]:
    return request_json("GET", base_url, token, f"/projects/{project_id}/views") or []


def find_view_id(base_url: str, token: str, project_id: int, view_name: str) -> int:
    views = list_views(base_url, token, project_id)
    for view in views:
        if view.get("title", "").strip().lower() == view_name.strip().lower():
            return int(view["id"])
    die(f"View not found: {view_name}")


def list_buckets(base_url: str, token: str, project_id: int, view_id: int) -> List[Dict[str, Any]]:
    return request_json("GET", base_url, token, f"/projects/{project_id}/views/{view_id}/buckets") or []


def find_bucket_id(base_url: str, token: str, project_id: int, view_id: int, bucket_name: str) -> int:
    buckets = list_buckets(base_url, token, project_id, view_id)
    for bucket in buckets:
        if bucket.get("title", "").strip().lower() == bucket_name.strip().lower():
            return int(bucket["id"])
    die(f"Bucket not found: {bucket_name}")


def extract_tasks(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        if data and isinstance(data[0], dict) and "tasks" in data[0]:
            tasks: List[Dict[str, Any]] = []
            for bucket in data:
                tasks.extend(bucket.get("tasks", []) or [])
            return tasks
        return data
    if isinstance(data, dict) and "tasks" in data:
        return data.get("tasks", []) or []
    return []


def list_tasks_for_view(base_url: str, token: str, project_id: int, view_id: int) -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    page = 1
    per_page = 100
    while True:
        data = request_json(
            "GET",
            base_url,
            token,
            f"/projects/{project_id}/views/{view_id}/tasks",
            params={"page": page, "per_page": per_page},
        )
        chunk = extract_tasks(data)
        if not chunk:
            break
        tasks.extend(chunk)
        if isinstance(data, list) and data and "tasks" in data[0]:
            break
        if len(chunk) < per_page:
            break
        page += 1
    return tasks


def get_task(base_url: str, token: str, task_id: int) -> Dict[str, Any]:
    return request_json("GET", base_url, token, f"/tasks/{task_id}")


def update_task(base_url: str, token: str, task: Dict[str, Any]) -> Dict[str, Any]:
    task_id = task.get("id")
    if not task_id:
        die("Cannot update task without id")
    return request_json("POST", base_url, token, f"/tasks/{task_id}", payload=task)


def create_task(base_url: str, token: str, project_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return request_json("PUT", base_url, token, f"/projects/{project_id}/tasks", payload=payload)


def list_labels(base_url: str, token: str) -> List[Dict[str, Any]]:
    return request_json("GET", base_url, token, "/labels", params={"page": 1, "per_page": 250}) or []


def find_label_id(base_url: str, token: str, label_name: str) -> Optional[int]:
    labels = list_labels(base_url, token)
    for label in labels:
        if label.get("title", "").strip().lower() == label_name.strip().lower():
            return int(label["id"])
    return None


def ensure_label_id(base_url: str, token: str, label_name: str) -> int:
    label_id = find_label_id(base_url, token, label_name)
    if label_id:
        return label_id
    created = request_json("PUT", base_url, token, "/labels", payload={"title": label_name})
    return int(created["id"])


def add_label_to_task(base_url: str, token: str, task_id: int, label_id: int) -> None:
    request_json("PUT", base_url, token, f"/tasks/{task_id}/labels", payload={"label_id": label_id})


def add_comment(base_url: str, token: str, task_id: int, comment: str) -> None:
    request_json("PUT", base_url, token, f"/tasks/{task_id}/comments", payload={"comment": comment})


def is_managed(description: str) -> bool:
    return MANAGED_MARKER in description


def render_template(template: str, values: Dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def status_block(summary_html: str, progress: str) -> str:
    today = date.today().isoformat()
    lines = [
        STATUS_START,
        "<p><strong>Sammanfattning:</strong></p>",
        summary_html,
        f"<p><strong>Progress:</strong> {escape_html(progress)}</p>",
        f"<p><strong>Senast uppdaterad:</strong> {today}</p>",
        STATUS_END,
    ]
    return "\n".join(lines)


def update_status_in_description(description: str, summary_html: str, progress: str) -> str:
    block = status_block(summary_html, progress)
    if STATUS_START in description and STATUS_END in description:
        before = description.split(STATUS_START)[0].rstrip()
        after = description.split(STATUS_END)[1].lstrip()
        return "\n".join([before, block, after]).strip() + "\n"
    return description.rstrip() + "\n\n" + block + "\n"




def escape_html(value: str) -> str:
    return html.escape(value, quote=True)


def format_html_block(value: str) -> str:
    value = value.strip()
    if not value:
        return "<p>–</p>"

    raw_lines = [line.rstrip() for line in value.splitlines()]
    lines = [line for line in raw_lines if line.strip()]
    if not lines:
        return "<p>–</p>"

    if all(_is_list_line(line) for line in lines):
        return _render_list(lines)

    escaped = "<br>".join(escape_html(line.strip()) for line in lines)
    return f"<p>{escaped}</p>"


def _is_list_line(line: str) -> bool:
    stripped = line.lstrip(" \t")
    return stripped.startswith(("-", "*"))


def _render_list(lines: list[str]) -> str:
    expanded = [line.replace("\t", "  ") for line in lines]
    min_indent = min(len(line) - len(line.lstrip(" ")) for line in expanded)
    items: list[tuple[int, str]] = []
    for line in expanded:
        indent = len(line) - len(line.lstrip(" "))
        content = line.lstrip()
        if content.startswith(("-", "*")):
            content = content[1:].lstrip()
        level = max(0, (indent - min_indent) // 2)
        items.append((min(level, 2), _apply_checkbox(content)))
    return _render_nested_list(items)


def _apply_checkbox(content: str) -> str:
    lowered = content.lower()
    if lowered.startswith("[ ]"):
        return "☐ " + content[3:].lstrip()
    if lowered.startswith("[x]"):
        return "☑ " + content[3:].lstrip()
    return content


def _render_nested_list(items: list[tuple[int, str]]) -> str:
    parts: list[str] = ["<ul>"]
    current_level = 0
    open_li = [False]

    for level, content in items:
        if level > current_level:
            while current_level < level:
                parts.append("<ul>")
                current_level += 1
                open_li.append(False)
        elif level < current_level:
            while current_level > level:
                if open_li[current_level]:
                    parts.append("</li>")
                    open_li[current_level] = False
                parts.append("</ul>")
                open_li.pop()
                current_level -= 1

        if open_li[current_level]:
            parts.append("</li>")
            open_li[current_level] = False

        parts.append(f"<li>{escape_html(content)}")
        open_li[current_level] = True

    while current_level > 0:
        if open_li[current_level]:
            parts.append("</li>")
        parts.append("</ul>")
        open_li.pop()
        current_level -= 1

    if open_li[0]:
        parts.append("</li>")
    parts.append("</ul>")
    return "".join(parts)


def parse_labels(raw: str) -> list[str]:
    return [label.strip() for label in raw.split(',') if label.strip()]


def ensure_labels_for_task(base_url: str, token: str, task_id: int, labels: list[str]) -> None:
    if not labels:
        return
    task = get_task(base_url, token, task_id)
    existing = {label.get("title", "").strip().lower() for label in task.get("labels", []) or []}
    for label in labels:
        if label.strip().lower() in existing:
            continue
        label_id = ensure_label_id(base_url, token, label)
        add_label_to_task(base_url, token, task_id, label_id)
        existing.add(label.strip().lower())


def remove_label_from_task(base_url: str, token: str, task_id: int, label_id: int) -> None:
    request_json('DELETE', base_url, token, f"/tasks/{task_id}/labels/{label_id}")


def replace_task_labels(base_url: str, token: str, task_id: int, label_ids: list[int]) -> None:
    request_json('POST', base_url, token, f"/tasks/{task_id}/labels/bulk", payload={"labels": label_ids})
def normalize_field(value: Optional[str]) -> str:
    if value is None:
        return "–"
    value = value.strip()
    return value if value else "–"


def task_matches_label(task: Dict[str, Any], label_name: str) -> bool:
    for label in task.get("labels", []) or []:
        if label.get("title", "").strip().lower() == label_name.lower():
            return True
    return False


def find_task_by_matching(
    tasks: List[Dict[str, Any]],
    pr_number: Optional[str],
    branch: Optional[str],
    title: Optional[str],
) -> Optional[Dict[str, Any]]:
    if pr_number:
        label_name = f"pr-{pr_number}"
        for task in tasks:
            if task_matches_label(task, label_name):
                return task
        title_prefix = f"[PR-{pr_number}]"
        for task in tasks:
            if task.get("title", "").startswith(title_prefix):
                return task
    if branch:
        marker = f"[branch:{branch}]"
        for task in tasks:
            if marker in task.get("title", ""):
                return task
            if marker in task.get("description", ""):
                return task
    if title and not pr_number and not branch:
        for task in tasks:
            if task.get("title", "").strip().lower() == title.strip().lower():
                return task
    return None


def load_asset(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def resolve_task(
    base_url: str,
    token: str,
    project_id: int,
    view_id: int,
    task_id: Optional[int],
    pr_number: Optional[str],
    branch: Optional[str],
    title: Optional[str],
) -> Optional[Dict[str, Any]]:
    if task_id:
        return get_task(base_url, token, task_id)
    tasks = list_tasks_for_view(base_url, token, project_id, view_id)
    return find_task_by_matching(tasks, pr_number, branch, title)


def cmd_ensure_task(args: argparse.Namespace) -> None:
    base_url = args.base_url or get_env("VIKUNJA_BASE_URL", required=True)
    token = args.token or get_env("VIKUNJA_API_TOKEN", required=True)

    if args.task_id:
        task = get_task(base_url, token, args.task_id)
        print(json.dumps({"action": "found", "task": task}, ensure_ascii=False, indent=2))
        return

    project_name = args.project or get_env("VIKUNJA_PROJECT_NAME", DEFAULT_PROJECT)
    view_name = args.view or get_env("VIKUNJA_VIEW_NAME", DEFAULT_VIEW)

    project_id = args.project_id or find_project_id(base_url, token, project_name)
    view_id = args.view_id or find_view_id(base_url, token, project_id, view_name)

    existing = resolve_task(
        base_url,
        token,
        project_id,
        view_id,
        None,
        args.pr_number,
        args.branch,
        args.title,
    )

    if existing:
        print(json.dumps({"action": "found", "task": existing}, ensure_ascii=False, indent=2))
        return

    bucket_name = args.bucket or DEFAULT_BUCKET
    bucket_id = find_bucket_id(base_url, token, project_id, view_id, bucket_name)

    if args.description:
        description = args.description
        if MANAGED_MARKER not in description:
            description = MANAGED_MARKER + "\n\n" + description
    else:
        template_path = os.path.join(os.path.dirname(__file__), "..", "assets", "task_description_template.md")
        template = load_asset(template_path)
        pr_section_html = ""
        if args.pr_url or args.pr_number:
            pr_label = args.pr_url or f"PR #{args.pr_number}"
            pr_section_html = "<h3>PR</h3>\n" + format_html_block(pr_label)
        description = render_template(
            template,
            {
                "goal_html": format_html_block(normalize_field(args.goal)),
                "requirements_html": format_html_block(normalize_field(args.requirements)),
                "solution_html": format_html_block(normalize_field(args.solution)),
                "definition_of_done_html": format_html_block(normalize_field(args.definition)),
                "pr_section_html": pr_section_html,
                "summary_html": escape_html("Ej påbörjat"),
                "progress": "0/0 (0%)",
                "date": date.today().isoformat(),
            },
        )

    title = args.title
    if args.pr_number and not title.startswith("[PR-"):
        title = f"[PR-{args.pr_number}] {title}"
    if args.branch:
        title = f"{title} [branch:{args.branch}]"

    payload = {
        "title": title,
        "description": description,
        "bucket_id": bucket_id,
    }

    created = create_task(base_url, token, project_id, payload)
    task_id = int(created.get("id"))

    if args.pr_number:
        label_id = ensure_label_id(base_url, token, f"pr-{args.pr_number}")
        add_label_to_task(base_url, token, task_id, label_id)

    if args.pr_url:
        add_comment(base_url, token, task_id, f"PR: {args.pr_url}")

    if args.labels:
        ensure_labels_for_task(base_url, token, task_id, parse_labels(args.labels))

    print(json.dumps({"action": "created", "task": created}, ensure_ascii=False, indent=2))


def cmd_progress_update(args: argparse.Namespace) -> None:
    base_url = args.base_url or get_env("VIKUNJA_BASE_URL", required=True)
    token = args.token or get_env("VIKUNJA_API_TOKEN", required=True)

    if args.task_id:
        task = get_task(base_url, token, args.task_id)
    else:
        project_name = args.project or get_env("VIKUNJA_PROJECT_NAME", DEFAULT_PROJECT)
        view_name = args.view or get_env("VIKUNJA_VIEW_NAME", DEFAULT_VIEW)

        project_id = args.project_id or find_project_id(base_url, token, project_name)
        view_id = args.view_id or find_view_id(base_url, token, project_id, view_name)

        task = resolve_task(
            base_url,
            token,
            project_id,
            view_id,
            None,
            args.pr_number,
            args.branch,
            args.title,
        )

    if not task:
        die("Task not found for progress update")

    done = args.done
    total = args.total
    ratio = 0.0
    if total and total > 0:
        ratio = done / total
    ratio = max(0.0, min(1.0, ratio))
    percent = round(ratio * 100)

    template_path = os.path.join(os.path.dirname(__file__), "..", "assets", "progress_comment_template.md")
    template = load_asset(template_path)
    comment = render_template(
        template,
        {
            "summary_html": format_html_block(normalize_field(args.summary)),
            "completed_html": format_html_block(normalize_field(args.completed)),
            "in_progress_html": format_html_block(normalize_field(args.in_progress)),
            "next_steps_html": format_html_block(normalize_field(args.next_steps)),
            "blockers_html": format_html_block(normalize_field(args.blockers)),
            "done": str(done),
            "total": str(total),
            "percent": str(percent),
        },
    )

    add_comment(base_url, token, int(task["id"]), comment)

    updated = get_task(base_url, token, int(task["id"]))
    updated["percent_done"] = ratio

    if is_managed(updated.get("description", "")):
        progress = f"{done}/{total} ({percent}%)" if total > 0 else "–"
        updated["description"] = update_status_in_description(
            updated.get("description", ""),
            format_html_block(normalize_field(args.summary)),
            progress,
        )

    update_task(base_url, token, updated)

    print(json.dumps({"action": "progress-updated", "task_id": task["id"], "percent_done": percent}, ensure_ascii=False, indent=2))


def cmd_link_pr(args: argparse.Namespace) -> None:
    base_url = args.base_url or get_env("VIKUNJA_BASE_URL", required=True)
    token = args.token or get_env("VIKUNJA_API_TOKEN", required=True)

    if args.task_id:
        task = get_task(base_url, token, args.task_id)
    else:
        project_name = args.project or get_env("VIKUNJA_PROJECT_NAME", DEFAULT_PROJECT)
        view_name = args.view or get_env("VIKUNJA_VIEW_NAME", DEFAULT_VIEW)

        project_id = args.project_id or find_project_id(base_url, token, project_name)
        view_id = args.view_id or find_view_id(base_url, token, project_id, view_name)

        task = resolve_task(
            base_url,
            token,
            project_id,
            view_id,
            None,
            args.pr_number,
            args.branch,
            args.title,
        )

    if not task:
        die("Task not found for PR link")

    if args.pr_number:
        label_id = ensure_label_id(base_url, token, f"pr-{args.pr_number}")
        add_label_to_task(base_url, token, int(task["id"]), label_id)

    if args.pr_url or args.pr_number:
        label = args.pr_url or f"PR #{args.pr_number}"
        add_comment(base_url, token, int(task["id"]), f"PR: {label}")

    print(json.dumps({"action": "linked-pr", "task_id": task["id"]}, ensure_ascii=False, indent=2))


def cmd_move_task(args: argparse.Namespace) -> None:
    base_url = args.base_url or get_env("VIKUNJA_BASE_URL", required=True)
    token = args.token or get_env("VIKUNJA_API_TOKEN", required=True)

    if args.task_id:
        task = get_task(base_url, token, args.task_id)
        project_id = args.project_id or int(task.get("project_id", 0))
    else:
        task = None
        project_id = 0

    project_name = args.project or get_env("VIKUNJA_PROJECT_NAME", DEFAULT_PROJECT)
    view_name = args.view or get_env("VIKUNJA_VIEW_NAME", DEFAULT_VIEW)

    if not project_id:
        project_id = find_project_id(base_url, token, project_name)

    view_id = args.view_id or find_view_id(base_url, token, project_id, view_name)

    if not task:
        task = resolve_task(
            base_url,
            token,
            project_id,
            view_id,
            None,
            args.pr_number,
            args.branch,
            args.title,
        )

    if not task:
        die("Task not found for move")

    bucket_id = find_bucket_id(base_url, token, project_id, view_id, args.to)

    updated = get_task(base_url, token, int(task["id"]))
    updated["bucket_id"] = bucket_id
    update_task(base_url, token, updated)

    print(json.dumps({"action": "moved", "task_id": task["id"], "bucket_id": bucket_id}, ensure_ascii=False, indent=2))




def cmd_labels(args: argparse.Namespace) -> None:
    base_url = args.base_url or get_env("VIKUNJA_BASE_URL", required=True)
    token = args.token or get_env("VIKUNJA_API_TOKEN", required=True)

    task_id = args.task_id
    task = get_task(base_url, token, task_id)
    existing = {label.get("title", "").strip().lower(): int(label["id"]) for label in task.get("labels", []) or []}

    if args.add:
        to_add = [label for label in parse_labels(args.add) if label.strip().lower() not in existing]
        ensure_labels_for_task(base_url, token, task_id, to_add)

    if args.remove:
        for label in parse_labels(args.remove):
            label_id = existing.get(label.strip().lower())
            if label_id:
                remove_label_from_task(base_url, token, task_id, label_id)

    if args.replace:
        label_ids = [ensure_label_id(base_url, token, label) for label in parse_labels(args.replace)]
        replace_task_labels(base_url, token, task_id, label_ids)

    print(json.dumps({"action": "labels-updated", "task_id": task_id}, ensure_ascii=False, indent=2))

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vikunja Kanban helper")
    parser.add_argument("--base-url", dest="base_url", help="Override VIKUNJA_BASE_URL")
    parser.add_argument("--token", dest="token", help="Override VIKUNJA_API_TOKEN")
    parser.add_argument("--project", help="Project name (default: Internal TODO)")
    parser.add_argument("--project-id", type=int, help="Project ID override")
    parser.add_argument("--view", help="View name (default: Kanban)")
    parser.add_argument("--view-id", type=int, help="View ID override")

    sub = parser.add_subparsers(dest="command", required=True)

    ensure = sub.add_parser("ensure-task", help="Find or create a task")
    ensure.add_argument("--title", required=True)
    ensure.add_argument("--description")
    ensure.add_argument("--goal")
    ensure.add_argument("--requirements")
    ensure.add_argument("--solution")
    ensure.add_argument("--definition")
    ensure.add_argument("--bucket", help="Bucket name (default: Idé)")
    ensure.add_argument("--pr-number")
    ensure.add_argument("--pr-url")
    ensure.add_argument("--branch")
    ensure.add_argument("--task-id", type=int)
    ensure.add_argument("--labels", help="Comma-separated labels to add")
    ensure.set_defaults(func=cmd_ensure_task)

    progress = sub.add_parser("progress-update", help="Post progress update and update percent_done")
    progress.add_argument("--task-id", type=int)
    progress.add_argument("--pr-number")
    progress.add_argument("--branch")
    progress.add_argument("--title")
    progress.add_argument("--done", type=int, required=True)
    progress.add_argument("--total", type=int, required=True)
    progress.add_argument("--summary")
    progress.add_argument("--completed")
    progress.add_argument("--in-progress", dest="in_progress")
    progress.add_argument("--next", dest="next_steps")
    progress.add_argument("--blockers")
    progress.set_defaults(func=cmd_progress_update)

    link = sub.add_parser("link-pr", help="Link a PR to a task")
    link.add_argument("--task-id", type=int)
    link.add_argument("--pr-number")
    link.add_argument("--pr-url")
    link.add_argument("--branch")
    link.add_argument("--title")
    link.set_defaults(func=cmd_link_pr)

    move = sub.add_parser("move-task", help="Move task to another bucket")
    move.add_argument("--task-id", type=int)
    move.add_argument("--pr-number")
    move.add_argument("--branch")
    move.add_argument("--title")
    move.add_argument("--to", required=True, help="Bucket name")
    move.set_defaults(func=cmd_move_task)

    labels_cmd = sub.add_parser("labels", help="Manage task labels")
    labels_cmd.add_argument("--task-id", type=int, required=True)
    labels_cmd.add_argument("--add", help="Comma-separated labels to add")
    labels_cmd.add_argument("--remove", help="Comma-separated labels to remove")
    labels_cmd.add_argument("--replace", help="Comma-separated labels to replace")
    labels_cmd.set_defaults(func=cmd_labels)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
