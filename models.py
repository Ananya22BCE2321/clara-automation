from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


@dataclass
class AccountMemo:
    account_id: str
    business_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_number: Optional[str] = None
    timezone: Optional[str] = None
    business_hours: Dict[str, Any] = field(default_factory=dict)
    emergency_definition: List[str] = field(default_factory=list)
    emergency_routing_rules: Dict[str, Any] = field(default_factory=dict)
    non_emergency_routing_rules: Dict[str, Any] = field(default_factory=dict)
    call_transfer_rules: Dict[str, Any] = field(default_factory=dict)
    integration_constraints: List[str] = field(default_factory=list)
    office_address: Optional[str] = None
    services_supported: List[str] = field(default_factory=list)
    after_hours_flow_summary: Optional[str] = None
    office_hours_flow_summary: Optional[str] = None
    notes: Optional[str] = None
    questions_or_unknowns: List[str] = field(default_factory=list)
    raw_transcript: Optional[str] = None
    created_at: str = field(default_factory=now_iso)


@dataclass
class RetellAgentSpec:
    version: str
    account_id: str
    prompt: str
    agent_name: Optional[str] = None
    voice_style: str = "professional"
    key_variables: Dict[str, Any] = field(default_factory=dict)
    tool_invocation_placeholders: List[str] = field(default_factory=list)
    call_transfer_protocol: Optional[str] = None
    fallback_protocol: Optional[str] = None
    created_at: str = field(default_factory=now_iso)


@dataclass
class ChangeLogEntry:
    field_path: str
    old: Any
    new: Any


@dataclass
class ChangeLog:
    account_id: str
    entries: List[ChangeLogEntry] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self):
        return {
            "account_id": self.account_id,
            "created_at": self.created_at,
            "entries": [asdict(e) for e in self.entries],
        }
