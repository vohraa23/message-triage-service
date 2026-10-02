# Decision Log

## What I built

A lightweight message-triage service using Python/FastAPI. It validates the incoming record, classifies one or more intents, extracts useful entities, detects risk, assigns confidence/priority, and routes the result to an appropriate handler or human review.

The design separates **classification** from **action policy**. Customer text is untrusted input. The model cannot directly execute refunds, payments, bookings, cancellations, or other external actions.

## What I chose not to build

I did not build real WhatsApp, Instagram, email, CRM, payment, airline, appointment, or recruiting integrations. The assignment supplies a local `messages.json` file and asks for a triage service, so external integrations would add complexity without improving the core assessment.

I also did not build a vector database, RAG system, fine-tuning pipeline, or agent framework. The task is classification/routing rather than knowledge retrieval or autonomous tool use.

## What I noticed in the data

The dataset includes prompt-injection text, null input, ambiguous context, multiple intents, medical/safety questions, transactional requests, urgent travel disruption, attachment references, and multilingual customer text. These cases drove the safety and escalation policy.

## Where this breaks

The service can struggle with messages that require missing conversation history, images/attachments that are not actually supplied, new intents outside the taxonomy, contradictory business policies, or LLM classification errors. A single message is not always enough context to make a safe decision.

## What I would do with another day

- Add a larger labeled evaluation set and regression tests.
- Add confidence calibration and precision/recall measurements by intent.
- Add structured logging, tracing, latency and cost metrics.
- Add queue-based asynchronous processing and a dead-letter queue.
- Add a human-review workflow and feedback loop.
- Add authenticated integrations with downstream systems.
- Add redaction/access controls for sensitive customer data.


## AI tools used

AI-assisted development was used during the implementation to help review the dataset, identify edge cases, and validate the overall approach.

The final implementation uses:

- Python-based deterministic rules for intent classification, entity extraction, risk detection, confidence handling, and routing decisions.
- Regular expressions and keyword-based matching for extracting information such as order IDs and amounts and for identifying specific message patterns.
- Pydantic models for validating and structuring input and output data.
- FastAPI for exposing the triage service through API endpoints.
- Pytest for testing important edge cases and validating the complete triage flow.
- Optional LLM support is included in the project, but the service can run fully without an API key. When enabled, the LLM is used only for structured classification assistance; the application-level policy rules remain responsible for human-review and safety decisions.
