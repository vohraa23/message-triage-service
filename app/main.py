import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from .models import IncomingMessage, TriageResult
from .triage import triage_message

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "messages.json"
OUTPUT_FILE = BASE_DIR / "outputs" / "results.json"

app = FastAPI(
    title="Message Triage Service",
    version="1.0.0",
    description="Take-home message triage service for GAJAN Group Holdings.",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/triage", response_model=TriageResult)
def triage_one(message: IncomingMessage):
    return triage_message(message)


@app.post("/triage/batch")
def triage_batch():
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read messages.json: {exc}")

    results = []
    for item in raw:
        try:
            msg = IncomingMessage.model_validate(item)
            results.append(triage_message(msg).model_dump())
        except Exception as exc:
            # One malformed record must not take down the batch.
            results.append({
                "message_id": str(item.get("id", "unknown")) if isinstance(item, dict) else "unknown",
                "error": type(exc).__name__,
                "requires_human": True,
                "action": "route_to_human_review",
                "handler": "human_review",
            })

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"count": len(results), "results_file": str(OUTPUT_FILE), "results": results}
