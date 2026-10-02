# Message Triage Service

A small Python/FastAPI service for the GAJAN Group Holdings take-home task. It reads the supplied `messages.json`, identifies customer intent(s), extracts useful entities, assigns priority and risk flags, and decides whether the message can be routed automatically or must go to a human.

The implementation deliberately separates **classification** from **action policy**. Customer messages are treated as untrusted data. An LLM may suggest a classification, but deterministic application rules decide whether human review is required.

## Why this design

The task contains deliberately messy cases: prompt injection, null text, ambiguous context, multiple intents, medical/safety questions, transactional requests, urgent travel disruption, and attachment references. The service is designed not to guess when the input is unsafe or insufficient.

## Project structure

```text
message-triage-service/
├── app/
│   ├── main.py       # FastAPI endpoints
│   ├── models.py     # Pydantic input/output schemas
│   ├── rules.py      # deterministic extraction, risk and policy rules
│   ├── llm.py        # optional OpenAI Responses API classifier
│   └── triage.py     # mode selection + fallback
├── data/messages.json
├── tests/test_triage.py
├── outputs/results.json
├── run_batch.py
├── requirements.txt
├── .env.example
└── DECISION_LOG.md
```

## Requirements

- Python 3.11+ recommended
- Internet only if using LLM mode
- OpenAI API key only if using LLM mode

## Setup

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run without an API key

This is the safest first run and requires no external service.

```bash
python run_batch.py
```

You should see:

```text
Processed 25 messages
Output: .../outputs/results.json
```

The deterministic mode is intentionally included as a fallback so the service can still run if the LLM is unavailable.

## Run the API

```bash
uvicorn app.main:app --reload
```

Open:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health

FastAPI exposes interactive Swagger documentation at `/docs` automatically.

## Optional LLM mode

Copy `.env.example` to `.env` and set:

```text
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-6-luna
TRIAGE_MODE=llm
```

Then run:

```bash
python run_batch.py
```

If an LLM call fails, the service falls back to deterministic rules and marks the result with `llm_fallback` and `requires_human=true`.

## API endpoints

### `GET /health`

Health check.

### `POST /triage`

Triage one message. Example request:

```json
{
  "id": "MSG-001",
  "brand": "vitalis-wellness",
  "channel": "whatsapp",
  "received_at": "2026-09-28T09:14:00+05:30",
  "text": "Hi, ordered the magnesium capsules on the 22nd, order VW-48812. Tracking hasn't moved in four days. Can you check?"
}
```

### `POST /triage/batch`

Reads `data/messages.json`, processes every record, and writes `outputs/results.json`.

## Output shape

Each successful result contains:

- `message_id`
- `brand`
- `channel`
- `intents[]` with confidence per intent
- `entities`
- `priority`
- `risk_flags`
- `action`
- `handler`
- `requires_human`
- overall `confidence`
- `reason`

## Human-review policy

A message is routed to a human when any of these apply:

1. text is null/empty;
2. confidence is below `0.75`;
3. prompt-injection indicators are present;
4. medical/product-safety advice is requested;
5. a financial/payment/refund action would be required;
6. an urgent/high-impact travel disruption is reported;
7. multiple intents include a transactional request;
8. the input is too ambiguous to resolve safely.

The LLM never directly executes an external action. It only proposes structured classification; local policy remains authoritative.

## Scaling to 10,000 messages/day

10,000/day is about 417 messages/hour or 7 messages/minute on average. The service is stateless and messages are independently processable. For production, I would place messages behind a durable queue such as SQS and run multiple workers horizontally. I would also add rate limiting, retries with backoff, dead-letter handling, observability, and a human-review queue.

The take-home remains local and intentionally avoids unnecessary cloud infrastructure.

## Cost model

Cost depends on the selected model, prompt size, output size, retries, and whether all messages go through the LLM. The README does not claim a fixed price without those measured assumptions.

For the final submission, record actual usage from the chosen model and calculate:

```text
cost_per_1k =
(1000 * average_input_tokens / 1,000,000 * input_price_per_1m)
+
(1000 * average_output_tokens / 1,000,000 * output_price_per_1m)
```

Then state the daily estimate as `10 * cost_per_1k` and monthly as approximately `300 * cost_per_1k`, before infrastructure and retry overhead.

## Testing

```bash
pytest -q
```

The tests specifically cover the supplied prompt-injection, null, ambiguous, medical-safety and full-25-message cases.

## AI tools used

AI-assisted development was used during the implementation to help review the dataset, identify edge cases, and validate the overall approach.

The final implementation uses:

- Python-based deterministic rules for intent classification, entity extraction, risk detection, confidence handling, and routing decisions.
- Regular expressions and keyword-based matching for extracting information such as order IDs and amounts and for identifying specific message patterns.
- Pydantic models for validating and structuring input and output data.
- FastAPI for exposing the triage service through API endpoints.
- Pytest for testing important edge cases and validating the complete triage flow.
- Optional LLM support is included in the project, but the service can run fully without an API key. When enabled, the LLM is used only for structured classification assistance; the application-level policy rules remain responsible for human-review and safety decisions.

No external AI-generated response is used directly as an action. Customer messages are treated as untrusted input, and the final routing decision is controlled by the application's deterministic policy rules.

## Important limitation

This is a triage service, not a system of record. It does not actually refund money, cancel subscriptions, book travel, change appointments, send messages, or access attachments. Those actions should be implemented behind authenticated business APIs and explicit authorization in a production system.
