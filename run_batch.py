import json
from pathlib import Path
from app.models import IncomingMessage
from app.triage import triage_message

root = Path(__file__).resolve().parent
input_file = root / "data" / "messages.json"
output_file = root / "outputs" / "results.json"

messages = json.loads(input_file.read_text(encoding="utf-8"))
results = [triage_message(IncomingMessage.model_validate(m)).model_dump() for m in messages]
output_file.parent.mkdir(exist_ok=True)
output_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Processed {len(results)} messages")
print(f"Output: {output_file}")
print(f"Human review: {sum(r['requires_human'] for r in results)}")
