import pytest
from pathlib import Path
from src.failure_memory.analyzer import FailureMemoryAnalyzer, canonicalize_failure_mode
from schemas.maintenance import MaintenanceRecord, FailureMemoryReport


@pytest.fixture
def analyzer():
    processed_dir = Path("data/processed/GA-1201A")
    return FailureMemoryAnalyzer.from_processed_dir(processed_dir)


def test_failure_mode_canonicalization():
    assert "High Vibration" in canonicalize_failure_mode("Unspecified", "Tripped on VSHH-1201 high vibration")
    assert "Mechanical Seal" in canonicalize_failure_mode("Unspecified", "Hexane leak at seal gland")
    assert "Shaft / Coupling" in canonicalize_failure_mode(None, "Rexnord coupling element cracked due to misalignment")
    assert "Bearing" in canonicalize_failure_mode("Unspecified", "Bearing DE noisy with high temperature")


def test_failure_pattern_summary(analyzer):
    summary = analyzer.get_pattern_summary("GA-1201A")
    assert summary.equipment_tag == "GA-1201A"
    assert summary.total_maintenance_records > 0
    assert summary.failure_count > 0
    assert summary.non_failure_count > 0
    assert summary.total_maintenance_records == summary.failure_count + summary.non_failure_count
    assert len(summary.top_failure_modes) > 0
    # Top mode should have a percentage > 0
    assert summary.top_failure_modes[0].percentage > 0.0


def test_find_similar_cases_vibration(analyzer):
    cases = analyzer.find_similar_cases("high vibration trip VSHH-1201", equipment_tag="GA-1201A", top_k=3)
    assert len(cases) > 0
    top_case = cases[0]
    assert "NT-2024-560011" in [c.event_id for c in cases]
    assert top_case.similarity_score > 0.3
    assert top_case.root_cause is not None


def test_find_similar_cases_seal_leak(analyzer):
    cases = analyzer.find_similar_cases("kebocoran mechanical seal hexane", equipment_tag="GA-1201A", top_k=3)
    assert len(cases) > 0
    seal_case = next((c for c in cases if "560005" in c.event_id), None)
    assert seal_case is not None
    assert "seal" in (seal_case.symptom or "").lower()


def test_rca_insights(analyzer):
    rca = analyzer.get_rca_insights("GA-1201A", symptom_keyword="vibration")
    assert rca.equipment_tag == "GA-1201A"
    assert len(rca.root_causes) > 0
    assert len(rca.proven_actions) > 0


def test_invariant_historical_evidence_not_current_diagnosis(analyzer):
    report = analyzer.analyze_failure_memory("getaran tinggi bearing DE", equipment_tag="GA-1201A")
    assert isinstance(report, FailureMemoryReport)
    assert "Historical evidence != Current diagnosis" in report.disclaimer
    assert report.has_historical_precedent is True
    assert len(report.similar_cases) > 0
