import os
from .models import IncomingMessage, TriageResult
from .rules import rule_triage


def triage_message(msg: IncomingMessage) -> TriageResult:
    mode = os.getenv("TRIAGE_MODE", "rules").lower()
    if mode == "llm":
        try:
            from .llm import llm_triage
            return llm_triage(msg)
        except Exception as exc:
            result = rule_triage(msg)
            result.risk_flags = sorted(set(result.risk_flags + ["llm_fallback"]))
            result.requires_human = True
            result.action = "route_to_human_review"
            result.handler = "human_review"
            result.reason += f" LLM path failed; deterministic fallback used: {type(exc).__name__}."
            return result
    return rule_triage(msg)
