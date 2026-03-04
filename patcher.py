from typing import Any, Dict, Tuple, List
from dataclasses import asdict, fields
from copy import deepcopy
from models import AccountMemo, ChangeLog, ChangeLogEntry


def _deep_update_and_diff(base: Dict[str, Any], updates: Dict[str, Any], path_prefix: str = "") -> Tuple[Dict[str, Any], List[ChangeLogEntry]]:
    """Return (updated_dict, list_of_change_entries) without mutating `base`."""
    updated = deepcopy(base)
    entries: List[ChangeLogEntry] = []

    for k, v in updates.items():
        path = f"{path_prefix}.{k}" if path_prefix else k
        base_val = base.get(k)

        # both lists -> merge, preserving existing items and adding new ones
        if isinstance(base_val, list) and isinstance(v, list):
            merged = base_val + [item for item in v if item not in base_val]
            if merged != base_val:
                entries.append(ChangeLogEntry(field_path=path, old=base_val, new=merged))
                updated[k] = merged
            continue

        # both dicts -> recurse merge
        if isinstance(base_val, dict) and isinstance(v, dict):
            sub_updated, sub_entries = _deep_update_and_diff(base_val, v, path)
            updated[k] = sub_updated
            entries.extend(sub_entries)
        else:
            old = base_val
            if old != v:
                entries.append(ChangeLogEntry(field_path=path, old=old, new=v))
                updated[k] = deepcopy(v)

    return updated, entries



def apply_patch(v1: AccountMemo, updates: Dict[str, Any]) -> Tuple[AccountMemo, ChangeLog]:
    # work from a JSON-serializable dict copy so original dataclass is not mutated
    v1_dict = asdict(v1)
    updated_dict, entries = _deep_update_and_diff(v1_dict, updates)

    # Filter updated_dict to AccountMemo fields only
    memo_field_names = {f.name for f in fields(AccountMemo)}
    filtered = {k: updated_dict.get(k) for k in updated_dict.keys() if k in memo_field_names}

    new_memo = AccountMemo(**filtered)

    changelog = ChangeLog(account_id=new_memo.account_id)
    changelog.entries = entries

    return new_memo, changelog
