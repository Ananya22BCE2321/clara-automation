import re
from typing import Dict, Any
from models import AccountMemo


PHONE_RE = re.compile(r"(\+?\d[\d\-\s()]{7,}\d)")
TIME_RE = re.compile(r"(open|opens|closed|close|from)\s+(\d{1,2})(:?\d{0,2})\s*(am|pm)?\s*(?:to|-)\s*(\d{1,2})(:?\d{0,2})\s*(am|pm)?",
                     flags=re.IGNORECASE)


def extract_demo_data(transcript: str) -> AccountMemo:
    transcript = transcript.strip()
    account_id = "unknown"
    memo = AccountMemo(account_id=account_id)
    memo.raw_transcript = transcript

    # business name heuristics
    m = re.search(r"(we are called|we're called|this is)\s+([A-Z][\w\s&,-]{1,80})", transcript, re.IGNORECASE)
    if m:
        memo.business_name = m.group(2).strip()

    # contact name heuristics
    m = re.search(r"my name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", transcript)
    if m:
        memo.contact_name = m.group(1).strip()

    # phone
    m = PHONE_RE.search(transcript)
    if m:
        memo.contact_number = m.group(1).strip()

    # timezone
    m = re.search(r"(timezone|time zone)[:\s]+([A-Za-z/_+-]{2,40})", transcript, re.IGNORECASE)
    if m:
        memo.timezone = m.group(2).strip()

    # business hours
    hrs = {}
    m = TIME_RE.search(transcript)
    if m:
        hrs['example'] = m.group(0)
        memo.business_hours = hrs

    # office address: look for patterns like "located at", "address is", "our office is at"
    m = re.search(r"(?:located at|address is|our office is at|office at)\s+([^.!?\n]{10,100})", transcript, re.IGNORECASE)
    if m:
        memo.office_address = m.group(1).strip()

    # services_supported: look for service keywords
    service_keywords = ["fire protection", "sprinkler", "alarm", "hvac", "electrical", "inspection", "extinguisher", "suppression"]
    found_services = []
    for keyword in service_keywords:
        if re.search(r"\b" + keyword + r"\b", transcript, re.IGNORECASE):
            found_services.append(keyword.lower())
    if found_services:
        memo.services_supported = list(set(found_services))  # deduplicate

    # emergency_definition: sentences with "emergency", "urgent", "immediate" combined with service words or context
    sentences = [s.strip() for s in re.split(r'[\n\.\!\?]+', transcript) if s.strip()]
    emergency_defs = []
    for s in sentences:
        if re.search(r"\b(emergency|urgent|immediate)\b", s, re.IGNORECASE):
            # Check if it mentions a service or context
            if any(kw in s.lower() for kw in service_keywords) or len(s) > 20:
                emergency_defs.append(s)
    if emergency_defs:
        memo.emergency_definition = emergency_defs

    # notes and unknowns
    if not memo.business_hours:
        memo.questions_or_unknowns.append("business_hours")
    if not memo.contact_name:
        memo.questions_or_unknowns.append("contact_name")
    if not memo.contact_number:
        memo.questions_or_unknowns.append("contact_number")
    if not memo.office_address:
        memo.questions_or_unknowns.append("office_address")
    if not memo.emergency_definition:
        memo.questions_or_unknowns.append("emergency_definition")
    if not memo.services_supported:
        memo.questions_or_unknowns.append("services_supported")

    # conservative: do not hallucinate other fields
    return memo


def extract_onboarding_updates(transcript: str) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}
    # timezone
    m = re.search(r"timezone[:\s]+([A-Za-z/_+-]{2,40})", transcript, re.IGNORECASE)
    if m:
        updates['timezone'] = m.group(1).strip()

    # business hours detailed
    m = TIME_RE.search(transcript)
    if m:
        updates['business_hours'] = {'example': m.group(0)}

    # contact info
    m = re.search(r"contact(?: name)?:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", transcript)
    if m:
        updates['contact_name'] = m.group(1).strip()

    m = PHONE_RE.search(transcript)
    if m:
        updates['contact_number'] = m.group(1).strip()

    # Routing rules extraction (conservative)
    # Split transcript into sentences to associate nearby timeout/fallback lines
    sentences = [s.strip() for s in re.split(r'[\n\.\!\?]+', transcript) if s.strip()]
    emergency_rules: Dict[str, Any] = {}
    non_emergency_rules: Dict[str, Any] = {}

    route_pattern = re.compile(r"(?:all\s+)?(?:emergency\s+)?([\w\s-]+?)\s+calls?\s+(?:must|should|will)?\s*(?:go to|be routed to|route to|goes to|send to)\s+([\w\s-]+)", re.IGNORECASE)
    timeout_pattern = re.compile(r"timeout(?:\s*(?:is|:))?\s*(\d{1,5})\s*seconds", re.IGNORECASE)
    fallback_pattern = re.compile(r"fallback(?:\s*(?:to|:))?\s*([\w\s-]+)", re.IGNORECASE)

    for idx, s in enumerate(sentences):
        m = route_pattern.search(s)
        if not m:
            continue
        raw_cat = m.group(1).strip()
        # normalize category (drop leading 'emergency' if present)
        cat = re.sub(r'^emergency\s+', '', raw_cat, flags=re.IGNORECASE).strip().lower()
        raw_route = m.group(2).strip().lower()
        # normalize route_to
        if 'dispatch' in raw_route:
            route_to = 'dispatch'
        elif 'phone' in raw_route and 'tree' in raw_route:
            route_to = 'phone_tree'
        elif 'custom' in raw_route:
            route_to = 'custom'
        else:
            route_to = raw_route.replace(' ', '_')

        cfg: Dict[str, Any] = {'route_to': route_to}

        # look in same sentence and next one for timeout/fallback
        window = s
        if idx + 1 < len(sentences):
            window = s + ' ' + sentences[idx + 1]

        tm = timeout_pattern.search(window)
        if tm:
            try:
                cfg['timeout_seconds'] = int(tm.group(1))
            except ValueError:
                pass

        fm = fallback_pattern.search(window)
        if fm:
            cfg['fallback_action'] = fm.group(1).strip()

        # Determine if this is emergency or non-emergency
        if re.search(r"\bemergency\b", s, re.IGNORECASE):
            emergency_rules[cat] = cfg
        else:
            non_emergency_rules[cat] = cfg

    if emergency_rules:
        updates['emergency_routing_rules'] = emergency_rules
    if non_emergency_rules:
        updates['non_emergency_routing_rules'] = non_emergency_rules

    # call_transfer_rules: extract timeout, retry count, fallback behavior
    transfer_rules: Dict[str, Any] = {}
    
    m = re.search(r"(?:global\s+)?timeout(?:\s*(?:is|:))?\s*(\d{1,5})\s*seconds", transcript, re.IGNORECASE)
    if m:
        try:
            transfer_rules['global_timeout'] = int(m.group(1))
        except ValueError:
            pass
    
    m = re.search(r"retry\s+(\d{1,3})\s*times?", transcript, re.IGNORECASE)
    if m:
        try:
            transfer_rules['retry_count'] = int(m.group(1))
        except ValueError:
            pass
    
    m = re.search(r"fallback(?:\s+(?:to|behavior))(?:\s*(?:is|:))?\s*([^.!?\n]{5,60})", transcript, re.IGNORECASE)
    if m:
        transfer_rules['fallback_behavior'] = m.group(1).strip()

    if transfer_rules:
        updates['call_transfer_rules'] = transfer_rules

    # integration_constraints: look for "never", "do not", "don't", "always" combined with system names or constraints
    constraint_pattern = re.compile(r"(?:never|do not|don't|always)\s+([^.!?\n]{10,100})", re.IGNORECASE)
    system_names = ["servicetrade", "servicetitan", "job", "ticket", "invoice", "dispatch", "crm"]
    constraints = []
    for s in sentences:
        m = constraint_pattern.search(s)
        if m:
            constraint_text = m.group(1).strip()
            # Check if it mentions system names or relevant keywords
            if any(sys in constraint_text.lower() for sys in system_names):
                constraints.append(constraint_text)
    
    if constraints:
        updates['integration_constraints'] = constraints

    return updates
