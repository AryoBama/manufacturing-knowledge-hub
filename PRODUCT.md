# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: plant engineers and maintenance/reliability staff at a petrochemical plant (Chandra Asri, Cilegon). They work at a desk or control-room workstation, troubleshooting equipment, checking specifications, interlock setpoints and failure history, and need an answer they can trace back to an approved document before acting on it.

Near-term audience: CALIBER 2026 competition judges evaluating a demo (Case 1: AI-Powered Industrial Knowledge Integration). Field operators on tablets are not a confirmed audience.

## Product Purpose

Connects plant knowledge that normally lives in separate files (OPL/SOP, P&ID, datasheets, interlock cause-and-effect, SAP PM maintenance history, plot plans) into one evidence-grounded hub. Engineers either ask questions in a chatbot or browse a Knowledge Repository by document type or by plant/area/equipment. Success is a correct, cited answer that an engineer can verify in the source document, and a refusal or flagged conflict when the evidence does not support one.

## Positioning

Answers are built from retrieved plant documents, not from a model's memory: every answer lists its source documents (with revision, status, page/sheet), flags conflicting values across revisions, checks approval status, and states a decomposed confidence. A generic chatbot could not truthfully claim that traceability. It also surfaces historical root causes and corrective actions for repeated failures.

## Operating Context

- Documents: Excel/PDF engineering records converted to JSON, identified by equipment tag (e.g. GA-1201A Hexane Feed Pump, KC-4501 Recycle Gas Compressor), document number, revision and approval status (Issued for Operation, Approved, Issued for Construction).
- Plant hierarchy: Plant, Area (e.g. 1200), Unit, Equipment, Component/Instrument.
- Safety-relevant domain: trip setpoints, start permissives and SIS logic. A wrong or uncited answer has real consequences.
- Runs via `docker compose up`: FastAPI backend plus the Svelte SPA behind nginx. An offline, deterministic answer mode exists so the system can run air-gapped; LLM providers (Gemini, DeepSeek, OpenAI) are optional.

## Capabilities and Constraints

- Chat: hybrid retrieval, answers with inline and listed citations, confidence level, recommended actions, clarification prompts. Per-point citation mapping is computed by the backend.
- Repository: browse by Type (document type) or Plant; equipment pages with a protection map; per-type document views; document detail with metadata, status and source text (page/sheet labels); "Ask Chatbot" hand-off.
- Failure Memory: search past incidents by symptom for a chosen equipment, with failure profile, similar incidents, root causes and proven fixes. Always shows that historical evidence is not a diagnosis.
- Not available yet: document upload (no ingestion endpoint; the UI says so), SOP and GA Drawing documents (categories exist, no data), area names for most areas (only Area 12 is described), GA-1201B has no documents.
- Chat history is stored in the browser only.
- UI language: English. The CALIBER 2026 casebook requires all submission materials (prototype, video, deck) in English. This replaces an earlier Bahasa Indonesia decision; plant users are Indonesian, so a translated interface remains a future option. Equipment tags, document titles and source text stay as in the data.
- Frontend currently loads Inter from Google Fonts; whether the pilot must be fully offline (no external requests) is undecided.

## Brand Commitments

Product name is a placeholder, "Chandra Asri Knowledge Hub" (set in `frontend/src/lib/config.ts`); a final name is undecided. No official logo or brand assets have been provided; the current mark is a generic factory icon. Do not imitate the company's official identity without supplied assets.

## Evidence on Hand

- Real sample dataset for GA-1201A under `GA-1201A HEXANE FEED PUMP/` and `data/extracted/`, plus KC-4501 and maintenance records for seven other tags.
- Benchmark and adversarial evaluation reports under `evaluation/`.
- Case brief: `The Case - CALIBER 2026.pdf`.
- No customer testimonials, usage metrics or pricing exist. Do not fabricate them.

## Product Principles

1. Evidence first: no claim without a visible, followable source; absence of evidence is stated, not papered over.
2. Operational safety over fluency: conflicts, obsolete revisions and low confidence are surfaced prominently rather than smoothed away.
3. Verify in one click: a citation leads to the exact document and section it came from.
4. Speak the engineer's language: plain English interface (the casebook requires English), plant terminology and tags kept exactly as written in the documents.
5. Honest about gaps: unavailable features and empty categories are labelled as such.

## Accessibility & Inclusion

No product-specific standard was established. Default expectation: keyboard-operable and readable in long desk sessions; citation markers and confidence/status must not rely on color alone.
