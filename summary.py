import json
from pathlib import Path
from typing import Dict, Any, List


BASE = Path(__file__).resolve().parent


def generate_summary() -> Dict[str, Any]:
    """
    Read all outputs/accounts/*/v1/memo.json and v2/memo.json if present.
    Return a summary table with account stats and save to outputs/summary.json.
    """
    accounts_dir = BASE / "outputs" / "accounts"
    
    if not accounts_dir.exists():
        print("No outputs/accounts directory found.")
        return {"accounts": [], "total_accounts": 0}
    
    summary_data = []
    
    for account_dir in sorted(accounts_dir.iterdir()):
        if not account_dir.is_dir():
            continue
        
        account_id = account_dir.name
        
        # Check for v1
        v1_memo_path = account_dir / "v1" / "memo.json"
        has_v1 = v1_memo_path.exists()
        v1_unknowns = 0
        
        if has_v1:
            with v1_memo_path.open("r", encoding="utf-8") as f:
                v1_memo = json.load(f)
                v1_unknowns = len(v1_memo.get("questions_or_unknowns", []))
        
        # Check for v2
        v2_memo_path = account_dir / "v2" / "memo.json"
        has_v2 = v2_memo_path.exists()
        
        # Check for changelog
        changelog_path = BASE / "changelogs" / f"{account_id}_changes.json"
        changelog_entries = 0
        
        if changelog_path.exists():
            with changelog_path.open("r", encoding="utf-8") as f:
                changelog = json.load(f)
                changelog_entries = len(changelog.get("entries", []))
        
        summary_data.append({
            "account_id": account_id,
            "has_v1": has_v1,
            "has_v2": has_v2,
            "questions_or_unknowns_count": v1_unknowns,
            "changelog_entries_count": changelog_entries,
        })
    
    result = {
        "total_accounts": len(summary_data),
        "accounts": summary_data,
    }
    
    # Save to outputs/summary.json
    output_dir = BASE / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result


def print_summary_table(summary: Dict[str, Any]):
    """Print summary as a formatted table."""
    accounts = summary.get("accounts", [])
    
    if not accounts:
        print("No accounts to summarize.")
        return
    
    # Print header
    print("\n" + "=" * 100)
    print(f"{'Account ID':<15} {'Has V1':<10} {'Has V2':<10} {'Unknowns':<15} {'Changelog Entries':<20}")
    print("=" * 100)
    
    # Print rows
    for acc in accounts:
        account_id = acc["account_id"]
        has_v1 = "✓" if acc["has_v1"] else "✗"
        has_v2 = "✓" if acc["has_v2"] else "✗"
        unknowns = acc["questions_or_unknowns_count"]
        changelog = acc["changelog_entries_count"]
        
        print(f"{account_id:<15} {has_v1:<10} {has_v2:<10} {unknowns:<15} {changelog:<20}")
    
    print("=" * 100)
    print(f"Total accounts: {summary.get('total_accounts', 0)}\n")


def main():
    print("Generating summary...")
    summary = generate_summary()
    print_summary_table(summary)
    print(f"Summary saved to {BASE / 'outputs' / 'summary.json'}")


if __name__ == "__main__":
    main()
