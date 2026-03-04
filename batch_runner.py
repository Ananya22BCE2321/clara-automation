import argparse
import glob
from pathlib import Path
from pprint import pprint

from storage import read_transcript, save_v1, save_v2, load_v1_memo
from extractor import extract_demo_data, extract_onboarding_updates
from agent_generator import generate_agent_spec
from patcher import apply_patch
from models import AccountMemo, RetellAgentSpec
from task_tracker import create_task


BASE = Path(__file__).resolve().parent


def run_demo():
    files = sorted(glob.glob(str(BASE / "data" / "demo" / "*.txt")))
    if not files:
        print("No demo transcripts found in data/demo/")
        return
    for f in files:
        account_id, text = read_transcript(f)
        # Idempotency guard: skip if v1 already exists
        v1_path = BASE / "outputs" / "accounts" / account_id / "v1"
        if v1_path.exists():
            print(f"v1 already exists for {account_id}, skipping.")
            continue
        memo = extract_demo_data(text)
        memo.account_id = account_id
        spec = generate_agent_spec(memo, version="v1")
        save_v1(account_id, memo, spec)
        # Track task
        output_path = str(BASE / "outputs" / "accounts" / account_id / "v1")
        create_task(account_id, "demo", output_path)
        print(f"Processed demo {account_id}")


def run_onboarding():
    files = sorted(glob.glob(str(BASE / "data" / "onboarding" / "*.txt")))
    if not files:
        print("No onboarding transcripts found in data/onboarding/")
        return
    for f in files:
        account_id, text = read_transcript(f)
        print(f"Onboarding: {account_id}")
        existing = load_v1_memo(account_id)
        if existing is None:
            print(f"v1 memo for {account_id} not found. Skipping.")
            continue
        updates = extract_onboarding_updates(text)
        if not updates:
            print(f"No explicit updates found for {account_id}")
            continue
        # construct AccountMemo from existing dict
        v1_memo = AccountMemo(**existing)
        v2_memo, changelog = apply_patch(v1_memo, updates)
        if not changelog.entries:
            print("No changes detected.")
            # Ensure we do not overwrite an existing v2
            v2_path = BASE / "outputs" / "accounts" / account_id / "v2"
            if v2_path.exists():
                print(f"Existing v2 found at {v2_path}; not overwriting.")
            continue
        spec_v2 = generate_agent_spec(v2_memo, version="v2")
        save_v2(account_id, v2_memo, spec_v2, changelog)
        # Track task
        output_path = str(BASE / "outputs" / "accounts" / account_id / "v2")
        create_task(account_id, "onboarding", output_path)
        print(f"Applied updates for {account_id}. Changes:")
        pprint([e.__dict__ for e in changelog.entries])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--onboarding", action="store_true")
    args = parser.parse_args()
    if args.demo:
        run_demo()
    if args.onboarding:
        run_onboarding()
    if not (args.demo or args.onboarding):
        parser.print_help()


if __name__ == "__main__":
    main()
