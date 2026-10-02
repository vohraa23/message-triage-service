from typing import Any, Literal
from pydantic import BaseModel, Field


class IncomingMessage(BaseModel):
    id: str
    brand: str
    channel: str
    received_at: str
    text: str | None = None


class Intent(BaseModel):
    name: str
    confidence: float = Field(ge=0, le=1)


class TriageResult(BaseModel):
    message_id: str
    brand: str
    channel: str
    intents: list[Intent]
    entities: dict[str, Any]
    priority: Literal["low", "normal", "high", "critical"]
    risk_flags: list[str]
    action: str
    handler: str
    requires_human: bool
    confidence: float = Field(ge=0, le=1)
    reason: str
