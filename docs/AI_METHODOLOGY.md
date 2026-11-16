# AI methodology

ASTRA HEALTH combines deterministic monitoring with an optional Gemini language-model API. It is an applied AI and software engineering prototype, with no custom training, medical prediction claim, or clinical validation.

## Model selection and integration

The implementation uses Google's `google-genai` Python SDK and defaults to `gemini-2.5-flash`. Gemini provides a hosted model and JSON-schema output support; the Flash configuration disables thinking and limits output to 1,000 tokens, making bounded interactive explanations practical. These are engineering reasons consistent with the code, not a documented comparison against other models. No latency, cost, or medical-quality benchmark has been established. `GEMINI_MODEL` can override the default; availability and configuration compatibility depend on the Google project.

`backend/ai.py:generate` creates a server-side client using `GEMINI_API_KEY`, API version `v1beta`, a 35-second SDK timeout, and one attempt. Analysis, chat, and report share this pipeline. Authentication, quota, model availability, transport, and malformed-response failures produce sanitized API errors. No key is embedded in the frontend. Missing credentials return HTTP 503; deterministic monitoring remains usable.

## Context and account boundaries

Private routes authenticate the opaque session cookie and derive the account on the server; caller-supplied account IDs do not select another user's data. Public demo endpoints use only bundled fictional profiles. Both routes require `consent: true` for AI requests. The UI also requires a consent checkbox before submission.

The model receives the requested mode, question, computed metrics (including baselines, deltas and trends), deterministic alerts, up to 14 recent check-ins including timestamps and free-text symptoms/well-being, and retrieved references. Profile name, email, mission and role are not separately included. Free text can still identify a person: field omission is not anonymization. Chat sends the current question and snapshot, not the full conversation. Private results and questions are saved in SQLite; demo results are not saved by the backend. Turning consent off prevents new UI requests; it does not erase prior transmissions or saved results.

## Lightweight reference retrieval

Four curated NASA summaries and URLs are bundled in `REFERENCES`. Retrieval always includes the general hazards reference and selects two of the other three by counting tag substrings in the question and alert codes. Ties preserve catalog order. This is local keyword ranking, not live NASA search, embeddings, a vector database, or retrieval of full scientific papers. Curated summaries may become stale, and lexical matching may miss relevant context.

## Structured output validation

The request supplies the JSON schema generated from the Pydantic `Narrative` model. The response must contain string lists for observations, changes, possible factors, follow-up, crew review, and enumerated source IDs; extra fields are forbidden. The server parses the JSON again with Pydantic and resolves source IDs against only the retrieved references. The model cannot supply arbitrary citation URLs through that field.

Schema validation establishes structure, not factual correctness. A valid narrative may still misinterpret evidence or cite a source that does not support its statement. There is no automated entailment check, medical expert review, or guarantee that every instruction is followed.

## Division of responsibility

| Deterministic Python (`backend/monitor.py`) | Gemini explanations |
| --- | --- |
| Validate numeric input ranges through API schemas | Summarize supplied records |
| Compute latest value minus personal baseline | Describe changes and possible factors with uncertainty |
| Compare latest three valid values with earlier values in the last seven check-ins, when at least four are valid | Suggest general reference-supported follow-up |
| Apply absolute baseline-offset demonstration thresholds | Answer questions about the supplied snapshot |
| Flag missing or older-than-36-hour data | Compose a structured daily report |
| Flag elevated heart rate plus symptoms, or reduced sleep plus fatigue | Return curated source IDs |

LLM output never recalculates the authoritative metrics or changes the deterministic alerts. The UI displays verified values separately from narrative. Thresholds in `backend/thresholds.json` are illustrative rules, not NASA medical standards. Sampling is check-in based rather than time-normalized; irregular intervals and missing data limit interpretation.

## Risk reduction and limitations

The system instruction treats questions and notes as untrusted input, restricts use to supplied sources and measurements, prohibits diagnosis/prescriptions/invented readings, asks for uncertainty, discourages numerical repetition, and requires existing crew-review flags to be carried forward. These instructions reduce risk but do not prove resistance to prompt injection or hallucination. Reference filtering restricts citation identities, not semantic accuracy. Deterministic alert panels remain independently available.

Tests mock Gemini to exercise all three response modes and selected errors. They do not evaluate a live model's factual quality. There is no labeled clinical dataset, sensitivity/specificity measurement, longitudinal astronaut study, or validated decision-support protocol. Internet connectivity, model access, quota, and provider data policies constrain cloud use. Review Google's current terms before enabling AI; use synthetic data for demonstrations.
