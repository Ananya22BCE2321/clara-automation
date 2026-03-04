# clara-automation

Lightweight Python pipeline to extract account memos from transcripts and produce Retell voice agent configurations for Clara Answers.

## Architecture

### Data Flow - Demo Pipeline (v1 Generation)

```
Transcript (.txt) 
  → extractor.extract_demo_data() 
  → AccountMemo (v1)
  → agent_generator.generate_agent_spec()
  → RetellAgentSpec
  → storage.save_v1()
  → outputs/accounts/<account_id>/v1/
```

The demo pipeline processes initial transcripts to create base account memos and agent specs. Each account generates a v1 memo and agent spec stored in `outputs/accounts/<account_id>/v1/`.

### Data Flow - Onboarding Pipeline (v2 Generation with Changelog)

```
Transcript (.txt)
  → extractor.extract_onboarding_updates()
  → Updates Dict
  → patcher.apply_patch() (merges with existing v1)
  → AccountMemo (v2) + ChangeLog
  → agent_generator.generate_agent_spec()
  → RetellAgentSpec
  → storage.save_v2() (also saves changes.json and changes.md)
  → outputs/accounts/<account_id>/v2/
```

The onboarding pipeline processes refinement transcripts, applies updates to existing v1 memos via deep-diff merge, generates v2 versions, and tracks all changes in a changelog.

### Key Components

- **models.py**: Dataclasses for `AccountMemo`, `RetellAgentSpec`, `ChangeLog`, `ChangeLogEntry`
- **extractor.py**: Regex-based extraction from transcripts (conservative, no LLMs)
- **agent_generator.py**: Builds prompts and agent specs from AccountMemo with explicit call routing steps
- **patcher.py**: Deep-diff merge engine for v1→v2 updates
- **storage.py**: JSON serialization and markdown changelog generation
- **batch_runner.py**: Orchestrates demo and onboarding pipelines
- **task_tracker.py**: Tracks processed accounts in `tasks/tasks.json`
- **summary.py**: Generates batch summary statistics

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Dataset Setup

### Folder Structure

- `data/demo/` : Place initial demo transcript files (.txt), one per account
  - Filename becomes the `account_id` (e.g., `demo1.txt` → `account_id="demo1"`)
  - Contents: unstructured call transcripts or notes

- `data/onboarding/` : Place refinement transcripts (.txt), one per existing account
  - Must match account_id of existing v1 memo
  - Contents: onboarding updates, new routing rules, constraints, etc.

- `outputs/accounts/<account_id>/v1/` : Auto-created
  - `memo.json`: Extracted AccountMemo from demo transcript
  - `agent_spec.json`: Generated RetellAgentSpec for v1

- `outputs/accounts/<account_id>/v2/` : Auto-created only if onboarding produces changes
  - `memo.json`: Merged AccountMemo (v1 + onboarding updates)
  - `agent_spec.json`: Updated RetellAgentSpec for v2

- `changelogs/` : Auto-created
  - `<account_id>_changes.json`: Machine-readable changelog with field-level diffs
  - `<account_id>_changes.md`: Human-readable markdown table of changes

- `tasks/tasks.json` : Auto-created
  - Log of all processed accounts with task_id, stage, timestamp, output paths

## Running the Pipeline

### Demo Pipeline (Create v1 Memos)

```bash
python -m batch_runner --demo
```

Processes all `.txt` files in `data/demo/`, extracts AccountMemo and generates RetellAgentSpec v1 for each.

### Onboarding Pipeline (Create v2 Memos)

```bash
python -m batch_runner --onboarding
```

Processes all `.txt` files in `data/onboarding/`, merges updates with existing v1 memos, and generates v2 memos with changelog tracking.

### Generate Summary Report

```bash
python summary.py
```

Reads all outputs and generates a summary table showing:
- Which accounts have v1/v2
- Number of unresolved questions per account
- Number of changelog entries per onboarding update

Output saved to `outputs/summary.json`.

### Web UI (optional)

A lightweight Flask-based interface lets you run the pipelines and view summaries from your browser. Install `Flask` (already included in `requirements.txt`), then start the server:

```bash
python app.py
```

Open `http://127.0.0.1:5000/` in your web browser. The home page provides buttons to:

- **Run Demo Pipeline** – processes files in `data/demo/` and saves v1 outputs.
- **Run Onboarding Pipeline** – processes `data/onboarding/` and saves v2 outputs.
- **Generate Summary** – refreshes the account summary table.

The page displays log output from each action and shows the current summary table by default.

This interface is purely optional and runs locally; it simply wraps the same Python functions used by the CLI scripts.

## Retell Manual Import

The Clara Answers free tier may not support Retell API access, so use this manual import workflow:

1. Generate agent specs:
   ```bash
   python -m batch_runner --demo
   ```

2. For each account, open the generated `agent_spec.json`:
   ```
   outputs/accounts/<account_id>/v1/agent_spec.json
   ```

3. Copy the `prompt` field from the JSON

4. In the Retell UI (https://retell.ai/):
   - Create a new Agent
   - Paste the prompt into the agent editor
   - Set `agent_name` field from the spec (e.g., "ACME Corp - Clara Agent")
   - Configure voice and other settings as needed
   - Test and deploy

5. For onboarding updates, repeat with v2 agent specs:
   ```
   outputs/accounts/<account_id>/v2/agent_spec.json
   ```

## Extracted Fields

### AccountMemo Fields (Demo & Onboarding)

**Demo Extraction (conservative):**
- `business_name`: Company name from "we are called", "we're called", "this is"
- `contact_name`: Person name from "my name is"
- `contact_number`: Phone number (regex)
- `timezone`: From "timezone:" or "time zone:"
- `business_hours`: Time ranges from patterns like "9am to 5pm"
- `office_address`: From "located at", "address is", "our office is at"
- `services_supported`: Keywords like fire protection, sprinkler, alarm, HVAC, electrical, etc.
- `emergency_definition`: Sentences mentioning "emergency", "urgent", "immediate"

**Onboarding Extraction (in addition to above):**
- `emergency_routing_rules`: Routes for categorized calls (e.g., "fire calls go to dispatch")
- `non_emergency_routing_rules`: Routes for non-emergency categories
- `call_transfer_rules`: Global timeout, retry count, fallback behavior
- `integration_constraints`: System constraints (e.g., "never create tickets in ServiceTitan without approval")

### RetellAgentSpec Fields

- `prompt`: Multi-step call flow prompts with explicit routing steps
- `agent_name`: Display name (e.g., "ACME Corp - Clara Agent")
- `voice_style`: Default "professional"
- `key_variables`: Dict with timezone, business_hours, office_address, emergency_routing
- `tool_invocation_placeholders`: Reserved tool names (e.g., "transfer_call", "send_sms_followup")

## Call Flow Structure

### Business Hours Flow (8 Steps)

(a) Greeting
(b) Ask purpose of call  
(c) Collect caller name and phone number
(d) Determine category and route/transfer
(e) Fallback if transfer fails
(f) Confirm next steps
(g) Ask "Is there anything else I can help you with?"
(h) Close call politely

### After Hours Flow (9 Steps)

(a) Greeting
(b) Ask purpose
(c) Confirm if emergency
(d) If emergency: collect name, number, AND office address immediately
(e) Attempt transfer
(f) If transfer fails: apologize and assure quick follow-up
(g) If non-emergency: collect details, confirm follow-up during business hours
(h) Ask "Is there anything else I can help you with?"
(i) Close politely

## Known Limitations

- **Extraction is Conservative & Heuristic-Based**: Regex patterns will miss edge cases and variations in phrasing. No NLP/LLM used, so accuracy depends on transcript formatting.
- **No Ambiguity Resolution**: If multiple phone numbers or names appear, only the first is extracted.
- **Timezone Support Limited**: Only recognizes standard timezone abbreviations and IANA timezone strings.
- **Tool Invocation Safety**: The prompt includes "Never mention tool names..." but this is advisory; the actual tool invocation logic must be enforced at the Retell API level.
- **No API Integration**: Free tier does not support direct Retell API calls; manual import required.
- **No Voice Customization**: Voice_style is hardcoded to "professional"; other voices require manual Retell UI configuration.
- **No Validation of Routing**: The system does not verify that the extracted routing destinations actually exist or are reachable.

## Improvements for Production

### High Priority
- **Robust NER with spaCy**: Replace regex extraction with spaCy Named Entity Recognition for contact names, addresses, and business entities.
- **Unit Tests**: Add comprehensive test coverage for patcher deep-diff behavior, changelog generation, and field extraction logic.
- **Logging Framework**: Use Python logging module instead of print statements for better observability and debugging.

### Medium Priority
- **Retell API Integration**: Implement direct API calls to Retell for agent creation and updates (requires paid tier).
- **Validation & Constraints**: Add a validation layer to check for required fields and warn on incomplete memos before saving.
- **Metrics & Monitoring**: Track extraction accuracy, field coverage, and processing time per account.
- **Webhook Support**: Expose an HTTP endpoint to trigger pipelines from external systems (e.g., CRM webhooks).
- **Incremental Updates**: Improve patcher to only update changed fields rather than deep-merging entire dicts.

### Low Priority
- **Multi-Language Support**: Add extraction patterns for other languages or expand service keyword lists by region.
- **Audio Processing**: Integrate with speech-to-text (e.g., Whisper) to extract transcripts from audio files directly.
- **Visualization Dashboard**: Build a web UI to browse accounts, view memos, and manually edit before agent deployment.
- **Export Formats**: Support export to other agent platforms (e.g., Twilio Studio, Voiceflow) via conversion templates.

## Example Usage

```python
# In Python REPL or script:
from pathlib import Path
from storage import read_transcript
from extractor import extract_demo_data
from agent_generator import generate_agent_spec

account_id, transcript = read_transcript("data/demo/acme.txt")
memo = extract_demo_data(transcript)
memo.account_id = account_id

spec = generate_agent_spec(memo)
print(spec.prompt)  # Full agent prompt
print(spec.key_variables)  # Timezone, hours, etc.
```

## Contributing

1. Add new extraction patterns to `extractor.py` (keep conservative and test-driven)
2. Extend call flows in `agent_generator.py` if Retell flow requirements change
3. Update tests in `tests/` folder
4. Update README with any new fields or behaviors

---

**Last Updated**: March 4, 2026  
**Maintainer**: Clara Answers Engineering
