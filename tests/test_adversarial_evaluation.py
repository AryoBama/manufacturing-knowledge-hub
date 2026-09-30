import pytest
from pathlib import Path
import json

from src.query.models import QueryRequest
from src.retrieval.retriever import HybridRetriever
from src.ingestion.document_loader import load_documents_from_dir

BASE_DIR = Path(__file__).resolve().parent.parent
ADV_FILE = BASE_DIR / "evaluation" / "adversarial_questions.json"
EXT_DIR = BASE_DIR / "data" / "extracted"


@pytest.fixture(scope="module")
def retriever():
    reg = load_documents_from_dir(EXT_DIR)
    return HybridRetriever(reg)


@pytest.fixture(scope="module")
def adversarial_cases():
    with open(ADV_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_adversarial_ghost_equipment_rejection(retriever, adversarial_cases):
    ghost_cases = [c for c in adversarial_cases if c["category"] == "ghost_equipment"]
    assert len(ghost_cases) >= 3

    for case in ghost_cases:
        req = QueryRequest(query=case["question"])
        resp = retriever.query(req)
        status_val = str(resp.sufficiency.status.value if hasattr(resp.sufficiency.status, "value") else resp.sufficiency.status)
        assert status_val in ("insufficient", "clarification_required")
        assert len(resp.results) == 0


def test_adversarial_cross_asset_contamination(retriever, adversarial_cases):
    cross_cases = [c for c in adversarial_cases if c["category"] == "cross_asset_contamination"]
    assert len(cross_cases) >= 3

    for case in cross_cases:
        req = QueryRequest(query=case["question"])
        resp = retriever.query(req)
        status_val = str(resp.sufficiency.status.value if hasattr(resp.sufficiency.status, "value") else resp.sufficiency.status)
        assert status_val == case["expected_sufficiency"]


def test_adversarial_false_technical_presuppositions(retriever, adversarial_cases):
    trap_cases = [c for c in adversarial_cases if c["category"] == "false_technical_presupposition"]
    assert len(trap_cases) >= 4

    for case in trap_cases:
        req = QueryRequest(query=case["question"])
        resp = retriever.query(req)
        assert resp.understanding.equipment_tag == case["expected_equipment"]
        status_val = str(resp.sufficiency.status.value if hasattr(resp.sufficiency.status, "value") else resp.sufficiency.status)
        assert status_val == "sufficient"
        top_ids = [r.chunk_id for r in resp.results[:3]]
        assert any(ev in top_ids for ev in case["expected_evidence"])


def test_adversarial_safety_bypass_guardrail(retriever, adversarial_cases):
    safe_cases = [c for c in adversarial_cases if c["category"] == "safety_violation_bypass"]
    assert len(safe_cases) >= 2

    for case in safe_cases:
        req = QueryRequest(query=case["question"])
        resp = retriever.query(req)
        assert resp.understanding.equipment_tag == "GA-1201A"
        assert resp.understanding.intent == "protection"
        top_ids = [r.chunk_id for r in resp.results[:3]]
        assert "TJC-LLD-IL-GA-1201A-P01-C01" in top_ids


def test_adversarial_noisy_entity_resolution(retriever, adversarial_cases):
    noisy_cases = [c for c in adversarial_cases if c["category"] == "noisy_entity_input"]
    assert len(noisy_cases) >= 3

    for case in noisy_cases:
        req = QueryRequest(query=case["question"])
        resp = retriever.query(req)
        assert resp.understanding.equipment_tag == "GA-1201A"
        status_val = str(resp.sufficiency.status.value if hasattr(resp.sufficiency.status, "value") else resp.sufficiency.status)
        assert status_val == "sufficient"


def test_adversarial_prompt_injection_resistance(retriever, adversarial_cases):
    inject_cases = [c for c in adversarial_cases if c["category"] == "prompt_injection_ood"]
    assert len(inject_cases) >= 2

    for case in inject_cases:
        req = QueryRequest(query=case["question"])
        resp = retriever.query(req)
        assert resp.understanding.equipment_tag == "GA-1201A"
        assert len(resp.results) > 0
