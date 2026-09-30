import pytest
from schemas.common import DocumentSource, DocumentStatus
from schemas.governance import ConflictType, ConflictRecord
from src.query.models import QueryUnderstanding
from src.retrieval.models import RetrievalResult, SufficiencyStatus
from src.retrieval.conflict import ConflictDetector
from src.retrieval.sufficiency import evaluate_evidence_sufficiency
from src.generation.evidence import EvidencePackage, EvidenceItem
from src.generation.synthesizer import DeterministicSynthesizer


def test_numeric_conflict_detection():
    src_a = DocumentSource(
        file_name="Interlock_Rev03.pdf",
        page=1,
        revision="Rev 3",
        status=DocumentStatus.ISSUED_FOR_OPERATION
    )
    src_b = DocumentSource(
        file_name="OPL_Rev02.pdf",
        page=1,
        revision="Rev 2",
        status=DocumentStatus.ISSUED_FOR_OPERATION
    )

    r1 = RetrievalResult(
        chunk_id="CHUNK-01",
        document_id="DOC-IL-01",
        document_type="INTERLOCK",
        equipment_tag="GA-1201A",
        content="Suction pressure trip setpoint PSLL-1201 < 0.5 barg initiates motor trip.",
        relevance_score=0.9,
        source=src_a
    )
    r2 = RetrievalResult(
        chunk_id="CHUNK-02",
        document_id="DOC-OPL-01",
        document_type="OPL",
        equipment_tag="GA-1201A",
        content="Field operator noted PSLL-1201 at 0.8 barg as safe trip threshold.",
        relevance_score=0.8,
        source=src_b
    )

    conflicts = ConflictDetector.detect_conflicts([r1, r2], equipment_tag="GA-1201A")
    assert len(conflicts) >= 1
    c = conflicts[0]
    assert c.conflict_type == ConflictType.NUMERIC_CONFLICT
    assert c.entity_tag == "PSLL-1201"
    assert c.resolution_status == "UNRESOLVED"
    assert "0.5" in c.value_a
    assert "0.8" in c.value_b


def test_revision_conflict_detection():
    src_old = DocumentSource(
        file_name="Datasheet_Rev01.pdf",
        page=1,
        revision="Rev 1",
        status=DocumentStatus.SUPERSEDED
    )
    src_new = DocumentSource(
        file_name="Datasheet_Rev02.pdf",
        page=1,
        revision="Rev 2",
        status=DocumentStatus.ISSUED_FOR_OPERATION
    )

    r1 = RetrievalResult(
        chunk_id="CHUNK-OLD",
        document_id="TJC-LLD-DS-GA-1201A-REV1",
        document_type="DATASHEET",
        equipment_tag="GA-1201A",
        content="Old specs for pump rated flow 40 m3/h.",
        relevance_score=0.7,
        source=src_old
    )
    r2 = RetrievalResult(
        chunk_id="CHUNK-NEW",
        document_id="TJC-LLD-DS-GA-1201A-REV2",
        document_type="DATASHEET",
        equipment_tag="GA-1201A",
        content="Updated specs for pump rated flow 45 m3/h.",
        relevance_score=0.9,
        source=src_new
    )

    conflicts = ConflictDetector.detect_conflicts([r1, r2], equipment_tag="GA-1201A")
    rev_c = [c for c in conflicts if c.conflict_type == ConflictType.REVISION_CONFLICT]
    assert len(rev_c) >= 1
    assert rev_c[0].resolution_status == "REVISION_RESOLVED"


def test_sufficiency_gate_flags_conflicting_evidence():
    src_a = DocumentSource(file_name="A.pdf", page=1, revision="Rev 1", status=DocumentStatus.ISSUED_FOR_OPERATION)
    src_b = DocumentSource(file_name="B.pdf", page=1, revision="Rev 2", status=DocumentStatus.ISSUED_FOR_OPERATION)

    r1 = RetrievalResult(
        chunk_id="C1",
        document_id="DOC-A",
        document_type="INTERLOCK",
        equipment_tag="GA-1201A",
        content="PSLL-1201 < 0.5 barg trips GA-1201A",
        relevance_score=0.85,
        source=src_a
    )
    r2 = RetrievalResult(
        chunk_id="C2",
        document_id="DOC-B",
        document_type="OPL",
        equipment_tag="GA-1201A",
        content="PSLL-1201 < 0.8 barg trips GA-1201A",
        relevance_score=0.80,
        source=src_b
    )

    from src.query.models import ResolutionMetadata, ResolutionSource, ResolutionConfidence
    res = ResolutionMetadata(
        source=ResolutionSource.EXPLICIT_QUERY,
        confidence=ResolutionConfidence.HIGH,
        candidate_tags=["GA-1201A"]
    )
    understanding = QueryUnderstanding(
        query="What is the trip setpoint of PSLL-1201?",
        intent="protection",
        equipment_tag="GA-1201A",
        knowledge_types=["protection"],
        resolution=res
    )


    check = evaluate_evidence_sufficiency(understanding, [r1, r2])
    assert check.status == SufficiencyStatus.CONFLICTING_EVIDENCE
    assert len(check.conflicts) >= 1


def test_synthesizer_renders_transparent_conflict_response():
    conflict = ConflictRecord(
        conflict_type=ConflictType.NUMERIC_CONFLICT,
        entity_tag="PSLL-1201",
        parameter_name="Trip limit for PSLL-1201",
        source_a=DocumentSource(file_name="Interlock_Rev03.pdf", page=1, revision="Rev 3", status=DocumentStatus.ISSUED_FOR_OPERATION),
        value_a="0.5 barg (INTERLOCK)",
        source_b=DocumentSource(file_name="OPL_Rev02.pdf", page=1, revision="Rev 2", status=DocumentStatus.ISSUED_FOR_OPERATION),
        value_b="0.8 barg (OPL)",
        resolution_status="UNRESOLVED",
        recommended_action="Verify against DCS Cause & Effect."
    )

    pkg = EvidencePackage(
        query="What is the trip limit of PSLL-1201?",
        equipment_tag="GA-1201A",
        intent="protection",
        items=[],
        sufficiency=SufficiencyStatus.CONFLICTING_EVIDENCE,
        sufficiency_reason="Conflicting engineering evidence detected.",
        conflicts=[conflict]
    )

    synthesizer = DeterministicSynthesizer()
    ans = synthesizer.generate(pkg)

    assert ans.requires_clarification is True
    assert "Conflicting evidence detected" in ans.summary_answer
    assert any("Source A: 0.5 barg" in pt for pt in ans.detailed_points)
    assert any("Source B: 0.8 barg" in pt for pt in ans.detailed_points)
