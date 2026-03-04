import os
import json
from dataclasses import asdict
from typing import Tuple
from pathlib import Path
from datetime import datetime

from models import AccountMemo, RetellAgentSpec, ChangeLog


BASE = Path(__file__).resolve().parent


def read_transcript(path: str) -> Tuple[str, str]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    account_id = p.stem
    return account_id, text


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, obj):
    _ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def _save_changes_markdown(account_id: str, changelog: ChangeLog):
    """Save a human-readable markdown file of changes to changelogs/ directory."""
    changelog_dir = BASE / "changelogs"
    _ensure_dir(changelog_dir)
    md_path = changelog_dir / f"{account_id}_changes.md"
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    lines = [
        f"# Changes for {account_id}",
        f"\nGenerated: {timestamp}",
        f"\nTotal changes: {len(changelog.entries)}",
        "\n## Change Log\n",
        "| Field | Old Value | New Value |",
        "|-------|-----------|-----------|",
    ]
    
    for entry in changelog.entries:
        old_val = str(entry.old) if entry.old is not None else "(empty)"
        new_val = str(entry.new) if entry.new is not None else "(empty)"
        # Escape pipes and newlines in values
        old_val = old_val.replace("|", "\\|").replace("\n", " ")
        new_val = new_val.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {entry.field_path} | {old_val} | {new_val} |")
    
    md_content = "\n".join(lines)
    with md_path.open("w", encoding="utf-8") as f:
        f.write(md_content)


def save_v1(account_id: str, memo: AccountMemo, agent_spec: RetellAgentSpec):
    base = BASE / "outputs" / "accounts" / account_id / "v1"
    _ensure_dir(base)
    memo_path = base / "memo.json"
    spec_path = base / "agent_spec.json"
    save_json(memo_path, asdict(memo))
    save_json(spec_path, asdict(agent_spec))
    print(f"Saved v1 for {account_id} -> {memo_path}")


def save_v2(account_id: str, memo_v2: AccountMemo, agent_spec_v2: RetellAgentSpec, changelog: ChangeLog):
    base = BASE / "outputs" / "accounts" / account_id / "v2"
    _ensure_dir(base)
    memo_path = base / "memo.json"
    spec_path = base / "agent_spec.json"
    save_json(memo_path, asdict(memo_v2))
    save_json(spec_path, asdict(agent_spec_v2))

    changelog_path = BASE / "changelogs"
    _ensure_dir(changelog_path)
    save_json(changelog_path / f"{account_id}_changes.json", changelog.to_dict())
    
    # Also save human-readable markdown
    _save_changes_markdown(account_id, changelog)
    
    print(f"Saved v2 and changelog for {account_id}")


def load_v1_memo(account_id: str):
    path = BASE / "outputs" / "accounts" / account_id / "v1" / "memo.json"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
