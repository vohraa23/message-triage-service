import json
from pathlib import Path
from app.models import IncomingMessage
from app.triage import triage_message

DATA = Path(__file__).resolve().parents[1] / "data" / "messages.json"


def load_messages():
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_all_25_messages_process_without_crashing():
    messages = load_messages()
    assert len(messages) == 25
    results = [triage_message(IncomingMessage.model_validate(m)) for m in messages]
    assert len(results) == 25


def test_prompt_injection_goes_to_human():
    msg = IncomingMessage.model_validate(load_messages()[4])
    result = triage_message(msg)
    assert result.requires_human is True
    assert "prompt_injection" in result.risk_flags


def test_null_message_goes_to_human():
    msg = IncomingMessage.model_validate(load_messages()[24])
    result = triage_message(msg)
    assert result.requires_human is True
    assert result.confidence == 0


def test_ambiguous_message_goes_to_human():
    msg = IncomingMessage.model_validate(load_messages()[11])
    result = triage_message(msg)
    assert result.requires_human is True


def test_medical_question_goes_to_qualified_support():
    msg = IncomingMessage.model_validate(load_messages()[18])
    result = triage_message(msg)
    assert result.requires_human is True
    assert result.handler == "qualified_support"
