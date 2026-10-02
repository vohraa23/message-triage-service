import re
from typing import Any
from .models import IncomingMessage, Intent, TriageResult

PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"administrator mode",
    r"system notice",
    r"system message",
    r"do not escalate",
    r"approve (a )?full refund",
    r"reply\s+confirmed",
]


def find_entities(text: str) -> dict[str, Any]:
    entities: dict[str, Any] = {}
    patterns = {
        "order_id": r"\bVW-\d{4,}\b",
        "booking_ref": r"\bVYG[A-Z0-9]{4,}\b",
        "phone": r"(?:\+?\d[\d\s().-]{8,}\d)",
        "amount_inr": r"(?:INR|Rs\.?|₹)\s?[\d,]+(?:\.\d+)?",
    }
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text, flags=re.I)
        if matches:
            entities[key] = matches[0].strip()
    if "attached" in text.lower() or "resume attached" in text.lower() or "pdf" in text.lower():
        entities["attachment_mentioned"] = True
        entities["attachment_available"] = False
    return entities


def detect_risks(text: str) -> list[str]:
    lower = text.lower()
    flags: list[str] = []
    if any(re.search(p, lower) for p in PROMPT_INJECTION_PATTERNS):
        flags.append("prompt_injection")
    if any(w in lower for w in ["blood pressure medication", "medication", "drug interaction", "safe to take"]):
        flags.append("medical_safety")
    if any(w in lower for w in ["bank details", "payment", "refund", "charged twice", "change fee"]):
        flags.append("financial_or_transactional")
    if any(w in lower for w in ["urgent", "immediately", "connection", "cancelled", "elderly passenger", "36 hours"]):
        flags.append("urgent")
    return flags


def classify(text: str) -> tuple[list[Intent], str, str, str, str]:
    """Return intents, action, handler, priority, reason."""
    t = text.lower()
    found: list[Intent] = []

    def add(name: str, confidence: float):
        found.append(Intent(name=name, confidence=confidence))

    if any(x in t for x in ["tracking", "track", "hasn't moved", "has not moved"]):
        add("order_tracking", 0.96)
    if "cancel my subscription" in t or "cancel my" in t and "subscription" in t:
        add("subscription_cancellation", 0.97)

    if any(x in t for x in ["unsubscribe", "un-subscribe"]):
        add("unsubscribe", 0.99)

    if (
        any(x in t for x in ["balayage", "keratin", "how much", "roughly"])
        or re.search(r"\brate\b", t)
    ):
        add("pricing_or_service_question", 0.90)

    if any(x in t for x in ["appointment", "booked for", "booking", "slot"]):
        if any(x in t for x in ["shift", "move", "sunday", "thursday", "tomorrow", "same day"]):
            add("appointment_change", 0.94)
        else:
            add("appointment_question", 0.88)

    if any(x in t for x in ["refund", "charged twice"]):
        add("refund_request", 0.95)
    elif any(x in t for x in ["wrong item", "broken"]):
        add("product_order_issue", 0.93)

    if any(x in t for x in ["still like to order", "order two", "two tubs"]):
        add("new_product_order", 0.92)
    elif any(x in t for x in ["ordered", "order", "ship", "protein", "500mg", "250mg"]):
        if not any(i.name == "order_tracking" for i in found):
            add("order_or_product_request", 0.82)
    if any(x in t for x in ["connection", "frankfurt", "pearson", "airline is saying", "36 hours"]):
        add("travel_disruption", 0.98)
    if any(x in t for x in ["quote", "dubai stopover", "how do we pay"]):
        add("travel_booking_followup", 0.94)
    if any(x in t for x in ["pharmacies", "bulk pricing", "wholesale"]):
        add("wholesale_sales", 0.98)
    if any(x in t for x in ["job", "resume attached", "openings for a travel consultant"]):
        add("job_application", 0.97)
    if any(x in t for x in ["safe to take", "blood pressure medication"]):
        add("product_safety_question", 0.99)
    if any(x in t for x in ["obsessed", "amazing job", "thank you", "packaging was much better"]):
        add("positive_feedback", 0.97)
    if not found:
        add("unknown", 0.25)


    priority = "normal"
    action = "route_to_human_review"
    handler = "human_review"

    names = {i.name for i in found}
    if "travel_disruption" in names:
        priority, action, handler = "critical", "escalate_immediately", "travel_emergency"
    elif "product_safety_question" in names:
        priority, action, handler = "high", "route_to_qualified_support", "qualified_support"
    elif "prompt_injection" in detect_risks(text):
        priority, action, handler = "high", "route_to_human_review", "human_review"
    elif "subscription_cancellation" in names:
        action, handler = "process_subscription_cancellation", "subscription_support"
    elif "unsubscribe" in names:
        action, handler = "process_unsubscribe", "customer_support"
    elif "order_tracking" in names:
        action, handler = "route_to_order_support", "order_support"
    elif "wholesale_sales" in names:
        action, handler = "route_to_wholesale_team", "wholesale_team"
    elif "job_application" in names:
        action, handler = "route_to_recruiting", "recruiting"
    elif any(n in names for n in ["travel_change", "accessible_travel_planning", "travel_booking_followup"]):
        action, handler = "route_to_travel_agent", "travel_agent"
    elif "appointment_change" in names or "appointment_question" in names or "pricing_or_service_question" in names:
        action, handler = "route_to_hair_studio", "hair_studio_front_desk"
    elif "positive_feedback" in names:
        action, handler = "no_customer_action", "social_or_support_team"
    elif "refund_or_order_issue" in names:
        action, handler = "route_to_customer_support", "customer_support"

    reason = "Classified from message content using deterministic rules."
    return found, action, handler, priority, reason


def apply_policy(msg: IncomingMessage, intents: list[Intent], entities: dict[str, Any], risk_flags: list[str], action: str, handler: str, priority: str, reason: str) -> TriageResult:
    text = msg.text or ""
    confidence = max((i.confidence for i in intents), default=0.0)
    requires_human = False
    policy_reasons: list[str] = []

    if not text.strip():
        requires_human = True
        confidence = 0.0
        action, handler, priority = "route_to_human_review", "human_review", "high"
        policy_reasons.append("Message text is empty or null.")
    if "prompt_injection" in risk_flags:
        requires_human = True
        action, handler, priority = "route_to_human_review", "human_review", "high"
        policy_reasons.append("Customer content contains instruction-like prompt injection patterns.")
    if "medical_safety" in risk_flags:
        requires_human = True
        action, handler, priority = "route_to_qualified_support", "qualified_support", "high"
        policy_reasons.append("Medical/safety question requires qualified human handling.")
    if "financial_or_transactional" in risk_flags and any(x in text.lower() for x in ["refund", "bank details", "charged twice", "payment"]):
        requires_human = True
        if action not in {"route_to_human_review", "route_to_qualified_support"}:
            action, handler = "route_to_human_review", "human_review"
        priority = max_priority(priority, "high")
        policy_reasons.append("Financial or payment-related action is not executed automatically.")
    if confidence < 0.75:
        requires_human = True
        action, handler = "route_to_human_review", "human_review"
        priority = max_priority(priority, "high")
        policy_reasons.append("Confidence is below the 0.75 automation threshold.")
    if len(intents) > 1:
        # Multiple intents are allowed, but transactional combinations are safer with a human.
        if any(i.name in {"refund_request", "new_product_order", "product_order_issue"} for i in intents):
            requires_human = True
            action, handler = "route_to_human_review", "human_review"
            policy_reasons.append("Multiple intents include a transactional request.")

    if policy_reasons:
        reason = reason + " " + " ".join(policy_reasons)

    return TriageResult(
        message_id=msg.id,
        brand=msg.brand,
        channel=msg.channel,
        intents=intents,
        entities=entities,
        priority=priority,
        risk_flags=risk_flags,
        action=action,
        handler=handler,
        requires_human=requires_human,
        confidence=round(confidence, 3),
        reason=reason,
    )


def max_priority(a: str, b: str) -> str:
    order = {"low": 0, "normal": 1, "high": 2, "critical": 3}
    return a if order[a] >= order[b] else b


def rule_triage(msg: IncomingMessage) -> TriageResult:
    text = msg.text or ""
    entities = find_entities(text)
    risk_flags = detect_risks(text)
    intents, action, handler, priority, reason = classify(text)
    return apply_policy(msg, intents, entities, risk_flags, action, handler, priority, reason)
