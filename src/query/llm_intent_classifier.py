import os
import json
import logging
import httpx
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

VALID_INTENTS = {
    "protection",
    "troubleshooting",
    "failure_history",
    "location",
    "procedure",
    "equipment_information",
    "general_information",
}

SYSTEM_PROMPT = """You are an industrial intent classifier for a plant engineering knowledge hub.
Classify the technical question into exactly ONE of the following controlled intents:
- protection: Interlock logic, trip limits, safety shutdowns, bypasses, setpoints (PSLL, VSHH, PSHH).
- troubleshooting: Symptoms, abnormal operation, remedies, root cause checks, sudden stops, leakage, high vibration.
- failure_history: Past failures, maintenance records, previous work orders, overhaul logs.
- location: Equipment physical location, plot plan, elevation, grid coordinates.
- procedure: Operating procedures, SOP, startup, shutdown sequences, priming, standard steps.
- equipment_information: Technical specifications, datasheets, design parameters, rated capacity, head, motor power.
- general_information: General concept questions, ambiguous queries, or queries unrelated to specific plant actions.

Rules:
1. DO NOT extract equipment tags or entities (entity resolution is handled externally).
2. DO NOT answer or resolve the query.
3. Respond ONLY with valid JSON matching this schema:
{
  "intent": "<one of the 7 valid intents above>",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "reason_code": "<snake_case reason, e.g. abnormal_operation_symptom>"
}
"""


class IntentClassificationResult(BaseModel):
    intent: str = Field(..., description="One of the controlled taxonomy intents")
    confidence: str = Field(default="HIGH", description="HIGH | MEDIUM | LOW")
    reason_code: str = Field(default="llm_inferred", description="Controlled snake_case rationale")


from src.adapters.llm import LLMAdapter, OfflineMockAdapter, get_llm_adapter


class LLMIntentClassifier:
    """
    Controlled LLM Semantic Intent Fallback Classifier.
    Invoked only when deterministic rules yield LOW or AMBIGUOUS confidence.
    Strictly isolated from entity resolution: classifies intent taxonomy ONLY.
    Delegates provider communication to the pluggable LLMAdapter.
    """

    def __init__(self, adapter: Optional[LLMAdapter] = None):
        self.adapter = adapter or get_llm_adapter()

    def classify(self, query: str) -> IntentClassificationResult:
        if isinstance(self.adapter, OfflineMockAdapter):
            return self._offline_semantic_fallback(query)

        try:
            raw_json = self.adapter.complete(
                prompt=f"Query: {query}",
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
                temperature=0.0,
            )
            cleaned = raw_json.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned).strip()
            if "{" in cleaned and "}" in cleaned:
                cleaned = cleaned[cleaned.find("{"):cleaned.rfind("}") + 1]

            data = json.loads(cleaned)
            intent = str(data.get("intent", "general_information")).lower()
            if intent not in VALID_INTENTS:
                intent = "general_information"

            return IntentClassificationResult(
                intent=intent,
                confidence=str(data.get("confidence", "HIGH")).upper(),
                reason_code=str(data.get("reason_code", "llm_inferred")),
            )
        except Exception as e:
            logger.warning("LLM intent classification failed (%s), falling back to semantic rules.", e)
            return self._offline_semantic_fallback(query)

    def _offline_semantic_fallback(self, query: str) -> IntentClassificationResult:
        """
        Lightweight deterministic semantic fallback for offline mode / unit tests
        handling natural-language phrasing and paraphrases.
        """
        q = query.lower()

        # Operational symptoms / sudden anomalies without explicit keyword 'troubleshoot'
        if (
            any(w in q for w in [
                "investigate", "high discharge temperature", "high temperature", "overheating",
                "abnormal noise", "abnormal vibration", "why does the pump stop", "why did it stop",
                "why does", "inspect after", "shaking", "shut unexpectedly", "hunting", "sluggish"
            ])
            or (("stop" in q or "trip" in q) and ("sudden" in q or "unexpected" in q or "running" in q))
            or (
                any(w in q for w in ["why does the pump stop", "why did it stop", "why does", "abnormal vibration", "inspect after", "shaking", "shut unexpectedly"])
                and any(w in q for w in ["stop", "trip", "check", "inspect", "vibration", "leak", "problem"])
            )
        ):
            return IntentClassificationResult(intent="troubleshooting", confidence="HIGH", reason_code="abnormal_operation_symptom")

        # Conversational failure inquiries
        if any(w in q for w in ["previous problem", "previous issue", "past trouble", "past issue", "ever failed"]):
            return IntentClassificationResult(intent="failure_history", confidence="HIGH", reason_code="conversational_failure_query")

        # Conversational protection inquiries
        if any(w in q for w in ["trips the pump", "what triggers trip", "cause shutdown"]):
            return IntentClassificationResult(intent="protection", confidence="HIGH", reason_code="conversational_protection_query")

        # Conversational location inquiries
        if any(w in q for w in ["where is", "where can i find", "physical layout"]):
            return IntentClassificationResult(intent="location", confidence="HIGH", reason_code="conversational_location_query")

        # Conversational procedure inquiries
        if any(w in q for w in ["how to execute", "how to perform", "guide to run", "operational step"]):
            return IntentClassificationResult(intent="procedure", confidence="HIGH", reason_code="conversational_procedure_query")

        return IntentClassificationResult(intent="general_information", confidence="LOW", reason_code="offline_fallback")


_DEFAULT_CLASSIFIER: Optional[LLMIntentClassifier] = None


def get_default_llm_intent_classifier() -> LLMIntentClassifier:
    global _DEFAULT_CLASSIFIER
    if _DEFAULT_CLASSIFIER is None:
        _DEFAULT_CLASSIFIER = LLMIntentClassifier()
    return _DEFAULT_CLASSIFIER
