#!/usr/bin/env python3
"""Trigger.dev CLI - Run tasks from the command line."""

import os
import sys
import json
import subprocess
import platform
import re
import requests

# Load .env files from current directory
try:
    from dotenv import load_dotenv
    load_dotenv(".env")  # Load base first
    load_dotenv(".env.local", override=True)  # Local overrides
except ImportError:
    pass  # dotenv not installed, rely on shell env

# Configuration from environment
API_KEY = os.environ.get("TRIGGER_SECRET_KEY")
PROJECT_ID = os.environ.get("TRIGGER_PROJECT_ID")
BASE_URL = "https://api.trigger.dev/api/v1"
BASE_URL_V2 = "https://api.trigger.dev/api/v2"

# Cache last listed tasks for quick selection
CACHE_FILE = os.path.expanduser("~/.trigger_last_tasks.json")


def print_help():
    print("""
trigger - Trigger.dev task runner

Usage:
    trigger                            List tasks (numbered)
    trigger list                       Same as above
    trigger list <search>              Search tasks by name
    trigger list --local               Scan ./tasks folder for all task definitions
    trigger schedules                  List scheduled tasks (numbered)
    trigger runs                       List recent runs with run IDs
    trigger runs --active              List only in-progress runs
    trigger run <task_id>              Run a task (asks for confirmation)
    trigger run <task_id> -y           Run without confirmation
    trigger run <task_id> -p <json>    Run with JSON payload
    trigger run <task_id> --open       Open run URL after trigger
    trigger cancel <run_id>            Cancel an in-progress run
    trigger cancel <number>            Cancel run by number from last 'trigger runs'
    trigger <number>                   Run task by number from last list
    trigger -h, --help                 Show this help

Environment:
    TRIGGER_SECRET_KEY   API key (tr_dev_... / tr_prod_...)
    TRIGGER_PROJECT_ID   Project ID (for dashboard URLs)
""".strip())


def open_url(url):
    """Open URL in browser (cross-platform)."""
    system = platform.system()
    try:
        cmd = "open" if system == "Darwin" else "xdg-open"
        subprocess.run([cmd, url], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        print(f"Open manually: {url}")


def confirm(message):
    """Ask for confirmation, return True if yes."""
    try:
        response = input(f"{message} [y/N] ").strip().lower()
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def list_tasks_local(search=None):
    """Scan ./tasks folder for task definitions."""
    tasks_dir = os.path.join(os.getcwd(), "tasks")
    if not os.path.isdir(tasks_dir):
        print("❌ No ./tasks folder found")
        return []

    task_ids = []
    id_pattern = re.compile(r"id:\s*['\"]([^'\"]+)['\"]")

    for root, _, files in os.walk(tasks_dir):
        for fname in files:
            if fname.endswith(".ts"):
                fpath = os.path.join(root, fname)
                with open(fpath, encoding="utf-8") as f:
                    content = f.read()
                for match in id_pattern.finditer(content):
                    tid = match.group(1)
                    # Skip template strings like $campaignId
                    if tid.startswith("$"):
                        continue
                    if search and search.lower() not in tid.lower():
                        continue
                    if tid not in task_ids:
                        task_ids.append(tid)

    tasks = [{"id": tid} for tid in sorted(task_ids)]

    with open(CACHE_FILE, "w") as f:
        json.dump(tasks, f)

    if search:
        print(f"Tasks matching '{search}' (local):")
    else:
        print("Tasks (local):")

    if not tasks:
        print("  (none found)")
        return tasks

    for i, t in enumerate(tasks, 1):
        print(f"  {i}. {t['id']}")

    return tasks


def list_tasks(search=None):
    """List tasks from recent runs, optionally filtered by search term."""
    response = requests.get(
        f"{BASE_URL}/runs",
        headers={"Authorization": f"Bearer {API_KEY}"},
        params={"page[size]": 100}
    )
    response.raise_for_status()

    runs = response.json().get("data", [])
    seen = {}
    tasks = []

    for run in runs:
        task_id = run.get("taskIdentifier")
        if not task_id or task_id in seen:
            continue
        if search and search.lower() not in task_id.lower():
            continue
        seen[task_id] = True
        tasks.append({
            "id": task_id,
            "status": run.get("status"),
            "updated": run.get("updatedAt", "")[:10]
        })

    # Save for quick selection
    with open(CACHE_FILE, "w") as f:
        json.dump(tasks, f)

    if search:
        print(f"Tasks matching '{search}':")
    else:
        print("Tasks:")

    if not tasks:
        print("  (none found)")
        return tasks

    for i, t in enumerate(tasks, 1):
        status_icon = "✓" if t["status"] == "COMPLETED" else "⏳"
        print(f"  {i}. {t['id']} {status_icon}")

    return tasks


def list_schedules():
    """List scheduled tasks."""
    response = requests.get(
        f"{BASE_URL}/schedules",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    response.raise_for_status()

    schedules = response.json().get("data", [])
    tasks = []

    print("Scheduled tasks:")
    for i, s in enumerate(schedules, 1):
        task_id = s.get("task")
        cron = s.get("generator", {}).get("expression", "")
        active = "🟢" if s.get("active") else "🔴"
        next_run = s.get("nextRun", "")[:16].replace("T", " ")

        tasks.append({"id": task_id, "schedule_id": s.get("id")})
        print(f"  {i}. {task_id} {active} [{cron}] next: {next_run}")

    # Save for quick selection
    with open(CACHE_FILE, "w") as f:
        json.dump(tasks, f)

    return schedules


RUNS_CACHE_FILE = os.path.expanduser("~/.trigger_last_runs.json")


def list_runs(active_only=False):
    """List recent runs with run IDs."""
    response = requests.get(
        f"{BASE_URL}/runs",
        headers={"Authorization": f"Bearer {API_KEY}"},
        params={"page[size]": 50}
    )
    response.raise_for_status()

    runs = response.json().get("data", [])

    if active_only:
        runs = [r for r in runs if r.get("status") not in ("COMPLETED", "FAILED", "CANCELED")]

    # Save for quick selection
    runs_cache = [{"run_id": r.get("id"), "task_id": r.get("taskIdentifier"), "status": r.get("status")} for r in runs]
    with open(RUNS_CACHE_FILE, "w") as f:
        json.dump(runs_cache, f)

    if active_only:
        print("In-progress runs:")
    else:
        print("Recent runs:")

    if not runs:
        print("  (none found)")
        return runs

    for i, r in enumerate(runs, 1):
        run_id = r.get("id", "")
        task_id = r.get("taskIdentifier", "")
        status = r.get("status", "")

        if status == "COMPLETED":
            icon = "✓"
        elif status in ("FAILED", "CANCELED"):
            icon = "✗"
        else:
            icon = "⏳"

        # Truncate run_id for display (show last 8 chars)
        short_id = run_id[-8:] if len(run_id) > 8 else run_id
        print(f"  {i}. {task_id} {icon} ({short_id})")

    return runs


def get_cached_run(number):
    """Get run ID from cache by number."""
    try:
        with open(RUNS_CACHE_FILE) as f:
            runs = json.load(f)
        return runs[number - 1]["run_id"]
    except (FileNotFoundError, IndexError, KeyError):
        return None


def cancel_run(run_id, skip_confirm=False):
    """Cancel an in-progress run."""
    if not skip_confirm:
        if not confirm(f"Cancel run '{run_id}'?"):
            print("Cancelled")
            return

    response = requests.post(
        f"{BASE_URL_V2}/runs/{run_id}/cancel",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    response.raise_for_status()

    print(f"✔️ Cancelled {run_id}")

    if PROJECT_ID:
        run_url = f"https://cloud.trigger.dev/projects/v3/{PROJECT_ID}/runs/{run_id}"
        print(f"   {run_url}")


def run_task(task_id, payload=None, auto_open=False, skip_confirm=False):
    """Trigger a task."""
    if not skip_confirm:
        if not confirm(f"Trigger '{task_id}'?"):
            print("Cancelled")
            return

    response = requests.post(
        f"{BASE_URL}/tasks/{task_id}/trigger",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={"payload": payload or {}}
    )
    response.raise_for_status()

    run_id = response.json().get("id")
    print(f"✔️ Triggered {task_id}")

    if PROJECT_ID and run_id:
        run_url = f"https://cloud.trigger.dev/projects/v3/{PROJECT_ID}/runs/{run_id}"
        print(f"   {run_url}")
        if auto_open:
            open_url(run_url)


def get_cached_task(number):
    """Get task ID from cache by number."""
    try:
        with open(CACHE_FILE) as f:
            tasks = json.load(f)
        return tasks[number - 1]["id"]
    except (FileNotFoundError, IndexError, KeyError):
        return None


def main():
    args = sys.argv[1:]

    # Handle help first (doesn't require API key)
    if "-h" in args or "--help" in args:
        print_help()
        return

    if not API_KEY:
        print("❌ TRIGGER_SECRET_KEY not set")
        sys.exit(1)

    # Handle flags
    skip_confirm = "-y" in args
    auto_open = "--open" in args
    args = [a for a in args if a not in ["-y", "--open"]]

    if not args:
        list_tasks()
        return

    if args[0] == "list":
        if "--local" in args:
            args = [a for a in args if a != "--local"]
            search = args[1] if len(args) > 1 else None
            list_tasks_local(search)
        else:
            search = args[1] if len(args) > 1 else None
            list_tasks(search)
    elif args[0] == "schedules":
        list_schedules()
    elif args[0] == "runs":
        active_only = "--active" in args
        list_runs(active_only)
    elif args[0] == "cancel":
        if len(args) < 2:
            print("Usage: trigger cancel <run_id|number>")
            sys.exit(1)

        target = args[1]
        if target.isdigit():
            run_id = get_cached_run(int(target))
            if not run_id:
                print("❌ Run 'trigger runs' first")
                sys.exit(1)
        else:
            run_id = target

        cancel_run(run_id, skip_confirm)
    elif args[0] == "run":
        if len(args) < 2:
            print("Usage: trigger run <task_id>")
            sys.exit(1)

        task_id = args[1]
        payload = None
        if "-p" in args:
            p_idx = args.index("-p")
            payload = json.loads(args[p_idx + 1])

        run_task(task_id, payload, auto_open, skip_confirm)
    elif args[0].isdigit():
        task_id = get_cached_task(int(args[0]))
        if not task_id:
            print("❌ Run 'trigger list' first")
            sys.exit(1)
        run_task(task_id, auto_open=auto_open, skip_confirm=skip_confirm)
    else:
        # Assume it's a task ID
        run_task(args[0], auto_open=auto_open, skip_confirm=skip_confirm)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.HTTPError as e:
        print(f"❌ API error: {e.response.status_code}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled")
