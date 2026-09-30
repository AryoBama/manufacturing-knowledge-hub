import pytest
import time
from pathlib import Path
from schemas.common import DocumentSource, DocumentStatus
from schemas.governance import ConflictRecord, ConflictType
from src.retrieval.models import SufficiencyStatus
from src.generation.evidence import EvidencePackage, EvidenceItem
from src.generation.models import ConfidenceLevel
from src.generation.confidence import ConfidenceCalculator
from src.observability.tracer import QueryTracer, QueryTraceRecord


def test_confidence_calculator_high():
    items = [
        EvidenceItem(
            evidence_id="EV-1",
            content="Rated Flow: 42 m3/h",
            equipment_tag="GA-1201A",
            document_id="DS-1201A",
            document_type="DATASHEET",
            source=DocumentSource(file_name="DS.pdf", page=1, status=DocumentStatus.APPROVED),
            relevance_score=0.92,
            evidence_type="technical_parameter"
        )
    ]
    package = EvidencePackage(
        query="Berapa flow rate GA-1201A?",
        equipment_tag="GA-1201A",
        intent="equipment_information",
        items=items,
        sufficiency=SufficiencyStatus.SUFFICIENT,
        sufficiency_reason="Approved datasheet found",
        covered_knowledge_types=["technical_parameter"]
    )

    level, reason, breakdown = ConfidenceCalculator.evaluate(package)
    assert level == ConfidenceLevel.HIGH
    assert breakdown.asset_match_score >= 0.95
    assert breakdown.source_validity_score == 1.0
    assert breakdown.final_score >= 0.75
    assert breakdown.conflict_penalty == 0.0


def test_confidence_calculator_conflict_penalty():
    items = [
        EvidenceItem(
            evidence_id="EV-1",
            content="PSLL = 0.5 barg",
            equipment_tag="GA-1201A",
            document_id="IL-1",
            document_type="INTERLOCK",
            source=DocumentSource(file_name="IL_Rev03.pdf", page=1, status=DocumentStatus.ISSUED_FOR_OPERATION),
            relevance_score=0.88,
            evidence_type="technical_parameter"
        )
    ]
    conflict = ConflictRecord(
        conflict_id="CONF-1",
        conflict_type=ConflictType.NUMERIC_CONFLICT,
        parameter_name="PSLL-1201 Setpoint",
        entity_tag="GA-1201A",
        value_a="0.5 barg",
        source_a=DocumentSource(file_name="IL_Rev03.pdf", page=1, status=DocumentStatus.ISSUED_FOR_OPERATION),
        value_b="0.8 barg",
        source_b=DocumentSource(file_name="OPL_Rev02.pdf", page=1, status=DocumentStatus.APPROVED),
        recommended_action="Audit setpoint"
    )
    package = EvidencePackage(
        query="Berapa setpoint PSLL GA-1201A?",
        equipment_tag="GA-1201A",
        intent="protection",
        items=items,
        sufficiency=SufficiencyStatus.CONFLICTING_EVIDENCE,
        sufficiency_reason="Conflicting values detected",
        conflicts=[conflict]
    )

    level, reason, breakdown = ConfidenceCalculator.evaluate(package)
    assert breakdown.conflict_penalty == 0.30
    assert "conflict" in reason.lower() or "contradictory" in reason.lower()
    assert level in (ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)


def test_query_tracer_latencies(tmp_path):
    tracer = QueryTracer("Berapa daya motor GA-1201A?")
    assert tracer.query_id.startswith("Q-")

    tracer.start_stage("nlu")
    time.sleep(0.005)
    nlu_ms = tracer.end_stage("nlu")
    assert nlu_ms > 0.0

    tracer.start_stage("retrieval")
    time.sleep(0.005)
    ret_ms = tracer.end_stage("retrieval")
    assert ret_ms > 0.0

    latencies = tracer.finalize()
    assert latencies.total_latency_ms >= (nlu_ms + ret_ms)
    assert latencies.query_id == tracer.query_id

    # Test audit logging
    record = QueryTraceRecord(
        query_id=tracer.query_id,
        timestamp=latencies.timestamp,
        query_text=tracer.query_text,
        equipment_tag="GA-1201A",
        latencies=latencies
    )
    log_file = tracer.log_audit(record, log_dir=tmp_path)
    assert log_file.exists()
    assert tracer.query_id in log_file.read_text(encoding="utf-8")
