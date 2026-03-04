import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from typing import List, Dict, Any


BASE = Path(__file__).resolve().parent
TASKS_DIR = BASE / "tasks"


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _get_tasks_file() -> Path:
    _ensure_dir(TASKS_DIR)
    return TASKS_DIR / "tasks.json"


def _load_tasks() -> List[Dict[str, Any]]:
    """Load all tasks from tasks.json."""
    tasks_file = _get_tasks_file()
    if not tasks_file.exists():
        return []
    with tasks_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_tasks(tasks: List[Dict[str, Any]]):
    """Save tasks to tasks.json."""
    tasks_file = _get_tasks_file()
    _ensure_dir(tasks_file.parent)
    with tasks_file.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def create_task(account_id: str, stage: str, output_path: str) -> str:
    """
    Create a new task entry and append to tasks/tasks.json.
    
    Args:
        account_id: The account identifier
        stage: "demo" or "onboarding"
        output_path: Path to the output (e.g., outputs/accounts/demo1/v1)
    
    Returns:
        task_id (uuid string)
    """
    task_id = str(uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    task = {
        "task_id": task_id,
        "account_id": account_id,
        "status": "pending",
        "stage": stage,
        "created_at": timestamp,
        "output_path": output_path,
    }
    
    tasks = _load_tasks()
    tasks.append(task)
    _save_tasks(tasks)
    
    return task_id


def list_tasks() -> List[Dict[str, Any]]:
    """
    List all tasks from tasks/tasks.json.
    
    Returns:
        List of task dictionaries
    """
    return _load_tasks()
