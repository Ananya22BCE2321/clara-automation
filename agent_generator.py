from models import AccountMemo, RetellAgentSpec


def _format_routing_block(rules: dict) -> str:
    parts = []
    for cat, cfg in rules.items():
        route_to = cfg.get("route_to", "dispatch")
        timeout = cfg.get("timeout_seconds", 20)
        fallback = cfg.get("fallback_action", "take message and schedule callback")
        parts.append(
            f"Category '{cat}': route_to={route_to}; timeout_seconds={timeout}; fallback_action={fallback}"
        )
        parts.append(
            "Transfer protocol: Attempt transfer to {dest}. If no answer within {t}s, perform: {fb}.".format(
                dest=route_to, t=timeout, fb=fallback
            )
        )
    return "\n".join(parts)


def generate_agent_spec(memo: AccountMemo, version: str = "v1") -> RetellAgentSpec:
    business = memo.business_name or "the company"
    greeting = f"Hello, thank you for contacting {business}."

    tz_line = f"Timezone: {memo.timezone}." if memo.timezone else "Timezone: unspecified."
    bh_line = "Business hours: unspecified."
    if memo.business_hours:
        bh_example = memo.business_hours.get("example") if isinstance(memo.business_hours, dict) else None
        if bh_example:
            bh_line = f"Business hours: {bh_example}."

    # Emergency routing
    emergency_block = ""
    if memo.emergency_routing_rules:
        emergency_block = (
            "Emergency Routing Rules:\n"
            + _format_routing_block(memo.emergency_routing_rules)
            + "\nEmergency triggers: "
            + (", ".join(memo.emergency_definition) if memo.emergency_definition else "(none specified)")
        )

    # Non-emergency routing
    non_emergency_block = ""
    if memo.non_emergency_routing_rules:
        non_emergency_block = (
            "Non-Emergency Routing Rules:\n" + _format_routing_block(memo.non_emergency_routing_rules)
        )

    # Call transfer global constraints
    transfer_constraints = ""
    if memo.call_transfer_rules:
        gtimeout = memo.call_transfer_rules.get("global_timeout", None)
        retries = memo.call_transfer_rules.get("retry_count", None)
        fallback = memo.call_transfer_rules.get("fallback_behavior", None)
        parts = []
        if gtimeout is not None:
            parts.append(f"global_timeout={gtimeout}s")
        if retries is not None:
            parts.append(f"retry_count={retries}")
        if fallback is not None:
            parts.append(f"fallback_behavior={fallback}")
        if parts:
            transfer_constraints = "Call Transfer Rules: " + "; ".join(parts)

    integration = ""
    if memo.integration_constraints:
        integration = "Integration constraints: " + ", ".join(memo.integration_constraints)

    # Business Hours Flow - explicit steps in order
    business_hours_flow = (
        "BUSINESS HOURS FLOW:\n"
        f"(a) Greeting: {greeting}\n"
        f"(b) Ask purpose of call: Determine the reason for contacting {business}.\n"
        "(c) Collect caller name and phone number immediately for reference and follow-up.\n"
        "(d) Determine category and route/transfer: Based on the purpose, identify the appropriate department or service.\n"
        "(e) Fallback if transfer fails: If the transfer is unsuccessful, offer to take a detailed message and schedule a callback.\n"
        "(f) Confirm next steps: Summarize what will happen next (e.g., department will call back within X hours).\n"
        "(g) Ask 'Is there anything else I can help you with?': Give the caller a chance to add additional information.\n"
        "(h) Close call politely: Thank them for calling and confirm they have the information they need.\n"
    )

    if emergency_block:
        business_hours_flow += (
            "\nEmergency Routing Rules:\n"
            + emergency_block
            + "\n"
        )

    if non_emergency_block:
        business_hours_flow += (
            "\nNon-Emergency Routing Rules:\n"
            + non_emergency_block
            + "\n"
        )

    if transfer_constraints:
        business_hours_flow += "\n" + transfer_constraints + "\n"

    if integration:
        business_hours_flow += "\n" + integration + "\n"

    # After Hours Flow - explicit steps in order
    after_hours_flow = (
        "AFTER HOURS FLOW:\n"
        f"(a) Greeting: {greeting}\n"
        "(b) Ask purpose: Determine the reason for the call and its urgency.\n"
        "(c) Confirm if emergency: Ask directly if this is an emergency situation.\n"
        "(d) If emergency: Immediately collect caller name, phone number, AND office address for dispatch purposes.\n"
        "(e) Attempt transfer: Try to connect to the appropriate department or emergency service based on the issue.\n"
        "(f) If transfer fails: Apologize and assure the caller that a representative will follow up immediately once business hours resume.\n"
        "(g) If non-emergency: Collect call details and confirm that a follow-up will happen during business hours.\n"
        "(h) Ask 'Is there anything else I can help you with?': Offer the caller a final opportunity to provide additional information.\n"
        "(i) Close politely: Thank them and confirm the expected follow-up timeline and contact method.\n"
    )

    if emergency_block:
        after_hours_flow += "\n" + emergency_block + "\n"

    # Build final prompt
    prompt_parts = [
        f"This is an operational agent script for account {memo.account_id}.",
        f"{tz_line} {bh_line}",
        business_hours_flow,
        after_hours_flow,
        "IMPORTANT INSTRUCTION: Never mention tool names, function calls, or system internals to the caller.",
        "Instructions: Be operational and concise. Only ask for explicit, verifiable information. Follow routing rules strictly."
    ]

    prompt = "\n\n".join([p for p in prompt_parts if p])

    # Create RetellAgentSpec with all new fields
    spec = RetellAgentSpec(
        version=version,
        account_id=memo.account_id,
        prompt=prompt,
        agent_name=f"{memo.business_name or memo.account_id} - Clara Agent",
        voice_style="professional",
        key_variables={
            "timezone": memo.timezone,
            "business_hours": memo.business_hours,
            "office_address": memo.office_address,
            "emergency_routing": memo.emergency_routing_rules,
        },
        tool_invocation_placeholders=["transfer_call", "send_sms_followup"],
        call_transfer_protocol="Announce transfer to caller before initiating. Attempt transfer to designated route. Wait for configured timeout. If no answer, execute fallback action.",
        fallback_protocol="If transfer fails: apologize to caller, confirm name and callback number, assure follow-up within business hours or emergency SLA, and close politely.",
    )

    return spec

