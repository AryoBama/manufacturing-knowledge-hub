from typing import Optional
from src.query.llm_intent_classifier import (
    IntentClassificationResult,
    VALID_INTENTS,
    get_default_llm_intent_classifier,
)


import re

_SECURITY_PATTERNS = [
    re.compile(r"\b(abaikan|ignore|bypass|forget|lewati|lupakan)\s+(semua\s+|all\s+)?(aturan|instruksi|dokumen|rule|instruction|prompt|guideline|policy|system|previous)", re.IGNORECASE),
    re.compile(r"\b(tanpa|without)\s+(menggunakan\s+|pakai\s+|using\s+|relying\s+on\s+)?(semua\s+|any\s+)?(rujukan|dokumen|sumber|referensi|citasi|citation|source|reference|evidence)", re.IGNORECASE),
    re.compile(r"\b(menurut|in your)\s+(pendapat|pengalaman|ingatan|memory|opinion|view|personal)", re.IGNORECASE),
    re.compile(r"\b(act as|berperan sebagai|pretend to be|roleplay|jailbreak|dan mode)\b", re.IGNORECASE),
    re.compile(r"\b(disregard|override)\s+(all|any)?\s*(safeguard|guardrail|rule|constraint|instruction)", re.IGNORECASE),
]


def is_jailbreak_or_prompt_injection(query: str) -> bool:
    """Detects prompt injection, system jailbreak, or policy bypass attempts using pattern matching."""
    q = query.strip()
    return any(pattern.search(q) for pattern in _SECURITY_PATTERNS)


def classify_intent_deterministic(query: str) -> IntentClassificationResult:
    """
    Step 1: Deterministic Intent Classifier.
    Assigns HIGH confidence for unambiguous plant keywords and patterns,
    or LOW confidence when ambiguous / no rules trigger.
    """
    q = query.lower()

    # Immediate Security Guard: Jailbreak / Prompt Injection returns general/security intent
    if is_jailbreak_or_prompt_injection(q):
        return IntentClassificationResult(
            intent="general_information",
            confidence="HIGH",
            reason_code="security_guardrail"
        )

    # Comparative equipment specification questions
    if any(k in q for k in ["same as", "sama seperti", "sama dengan", "compare pump", "versus", "equivalent"]):
        return IntentClassificationResult(
            intent="equipment_information",
            confidence="HIGH",
            reason_code="comparative_specification"
        )

    # Troubleshooting & Anomaly Diagnosis (check first-check / diagnostic questions before history)
    if any(k in q for k in [
        "what is the first check", "first check", "what should i check", "how to fix", "remedy",
        "troubleshoot", "diagnostic", "abnormal", "anomali", "investigate", "investigasi",
        "what should operators investigate", "what should operator investigate",
        "what should we check", "how to inspect", "what to check", "what should check"
    ]):
        return IntentClassificationResult(
            intent="troubleshooting",
            confidence="HIGH",
            reason_code="explicit_troubleshooting_keyword"
        )

    # Operational Procedures & SOP
    if any(k in q for k in [
        "how to start", "how to perform", "start-up", "startup", "procedure", "prosedur", "sop",
        "step-by-step", "operating steps", "langkah operasi", "langkah kerja", "cara start",
        "priming", "pre-start", "alignment", "aligment", "toleransi", "tolerance", "coupling alignment"
    ]):
        return IntentClassificationResult(
            intent="procedure",
            confidence="HIGH",
            reason_code="explicit_procedure_keyword"
        )

    # Past Incidents / Maintenance History (check before general troubleshooting keywords like leak)
    if any(k in q for k in [
        "failed before", "history", "past failure", "past incident", "maintenance record",
        "root cause", "rca", "past trouble", "downtime", "breakdown", "replacement", "replaced", "repair",
        "pemeliharaan", "riwayat", "kerusakan", "perbaikan", "riwayat kerusakan",
        "work order", "wo-", "corrective action", "experienced", "experience", "past work",
        "did compressor", "did pump", "did ea-", "did yd-", "have valve leakage issues"
    ]):
        return IntentClassificationResult(
            intent="failure_history",
            confidence="HIGH",
            reason_code="explicit_failure_history_keyword"
        )

    # Protection & Safety Interlock Logic (ensure bypass matches industrial interlock context)
    if any(k in q for k in [
        "trip condition", "trip limit", "interlock", "permissive", "cause & effect",
        "cause and effect", "shutdown logic", "can trip", "to trip", "trip on",
        "trips", "trip", "jumper", "bypass interlock", "bypass trip", "bypass safety", "override trip", "override interlock", "shut down", "shutdown",
        "kondisi trip", "batas trip", "proteksi", "psll", "pshh", "fsll", "vshh",
        "setpoint", "conflict", "konflik"
    ]):
        return IntentClassificationResult(
            intent="protection",
            confidence="HIGH",
            reason_code="explicit_protection_keyword"
        )

    # Troubleshooting & Anomaly Diagnosis (general anomaly signals)
    if any(k in q for k in [
        "vibrat", "leak", "high temp", "high temperature", "discharge temp", "discharge temperature",
        "overheat", "overheating", "suhu tinggi", "temperatur tinggi", "temperature high",
        "getar", "bocor", "kebocoran", "panas", "gangguan", "bearing", "noise", "bising", "bunyi",
        "cavitation", "kavitasi", "misalignment", "seal leak", "fouling", "hunting", "sluggish"
    ]):
        return IntentClassificationResult(
            intent="troubleshooting",
            confidence="HIGH",
            reason_code="anomaly_symptom"
        )

    # Plant Location & Physical Layout
    if any(k in q for k in [
        "where is", "located", "location", "plot plan", "layout", "elevation", "grid ref",
        "lokasi", "letak", "posisi", "di mana"
    ]):
        return IntentClassificationResult(
            intent="location",
            confidence="HIGH",
            reason_code="explicit_location_keyword"
        )

    # Equipment Specs / Datasheet Information
    if any(k in q for k in [
        "what is", "spec", "spesifikasi", "datasheet", "rated flow", "capacity", "kapasitas",
        "aliran", "flow", "motor power", "daya", "daya motor", "penggerak", "drawing", "material",
        "driver", "driven", "driven by", "turbine", "power", "head", "compression ratio",
        "data teknik", "tampilkan data", "apa itu", "apa spesifikasi", "old document", "dokumen lama",
        "show details", "details for", "show", "data", "pressure", "suction pressure", "bar",
        "temperature", "temp", "suhu", "design temp", "operating temp"
    ]):
        return IntentClassificationResult(
            intent="equipment_information",
            confidence="HIGH",
            reason_code="explicit_spec_keyword"
        )

    # Unmatched / Ambiguous -> LOW confidence triggers LLM semantic fallback
    return IntentClassificationResult(
        intent="general_information",
        confidence="LOW",
        reason_code="unmatched_deterministic_rule"
    )


def classify_intent_hybrid(query: str, fallback_to_llm: bool = True) -> IntentClassificationResult:
    """
    High-Performance Hybrid Intent Classifier:
    1. Deterministic Security Guard: Blocks prompt injection / jailbreak queries immediately (0.1ms).
    2. High-Precision Rules: If unambiguous industrial patterns match with HIGH confidence,
       resolves immediately in 0.1ms without incurring 30s LLM network roundtrip.
    3. Semantic LLM Fallback: For conversational, ambiguous, or unmatched queries, leverages
       LLM classifier for nuanced intent resolution.
    """
    q = query.strip()

    # Step 1: Immediate Security Guard (Deterministic)
    if is_jailbreak_or_prompt_injection(q):
        return IntentClassificationResult(
            intent="general_information",
            confidence="HIGH",
            reason_code="security_guardrail"
        )

    # Step 2: High-Precision Deterministic Rules (Instant 0.1ms)
    det_result = classify_intent_deterministic(q)
    if det_result.confidence == "HIGH":
        return det_result

    # Step 3: Semantic LLM Classification for ambiguous / conversational phrasing
    if fallback_to_llm:
        try:
            llm = get_default_llm_intent_classifier()
            llm_result = llm.classify(q)
            if (
                llm_result.intent in VALID_INTENTS
                and llm_result.confidence in ("HIGH", "MEDIUM")
                and llm_result.reason_code != "offline_fallback"
            ):
                return llm_result
        except Exception:
            pass

    return det_result


def classify_intent(query: str, fallback_to_llm: bool = True) -> str:
    """
    Backward-compatible entry point returning the canonical intent string.
    """
    return classify_intent_hybrid(query, fallback_to_llm=fallback_to_llm).intent

