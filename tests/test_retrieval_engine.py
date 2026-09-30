from pathlib import Path
from schemas.common import DocumentSource, DocumentStatus
from src.query.models import QueryRequest, QueryUnderstanding, ResolutionMetadata, ResolutionSource, ResolutionConfidence
from src.ingestion.document_loader import load_documents_from_dir
from src.retrieval.models import RetrievalResult, SufficiencyStatus
from src.retrieval.metadata_filter import filter_by_metadata
from src.retrieval.lexical import compute_lexical_score
from src.retrieval.semantic import compute_semantic_score
from src.retrieval.sufficiency import evaluate_evidence_sufficiency
from src.retrieval.retriever import HybridRetriever


def test_metadata_filter():
    base_dir = Path(__file__).resolve().parent.parent
    ext_dir = base_dir / "data" / "extracted"
    registry = load_documents_from_dir(ext_dir)
    chunks = registry.get_all()

    filtered = filter_by_metadata(chunks, equipment_tag="GA-1201A", allowed_document_types=["DATASHEET"])
    assert len(filtered) == 1
    assert filtered[0].document_type == "DATASHEET"
    assert filtered[0].equipment_tag == "GA-1201A"


def test_lexical_and_semantic_matching():
    query = "What should I check when GA-1201A has high vibration?"
    content = "LOGIC No: SEQ-1201. Bearing vibration HIGH-HIGH on GA-1201A trips motor."

    lex = compute_lexical_score(query, content, target_tag="GA-1201A")
    sem = compute_semantic_score(query, content)

    assert lex > 0.4
    assert sem > 0.2


def test_evidence_sufficiency_four_pillars():
    und_base = QueryUnderstanding(
        query="What conditions can trip GA-1201A?",
        intent="protection",
        equipment_tag="GA-1201A",
        resolution=ResolutionMetadata(source=ResolutionSource.EXPLICIT_QUERY, confidence=ResolutionConfidence.HIGH),
        knowledge_types=["protection_logic", "process_logic"]
    )

    valid_src = DocumentSource(
        file_name="interlock.pdf",
        page=1,
        revision="Rev 3",
        status=DocumentStatus.ISSUED_FOR_OPERATION
    )
    res_valid = RetrievalResult(
        chunk_id="CHK-01",
        document_id="DOC-01",
        document_type="INTERLOCK",
        equipment_tag="GA-1201A",
        content="Vibration HIGH-HIGH trips pump motor.",
        relevance_score=0.85,
        source=valid_src
    )

    # 1. Sufficient condition
    check_ok = evaluate_evidence_sufficiency(und_base, [res_valid])
    assert check_ok.status == SufficiencyStatus.SUFFICIENT
    assert "protection_logic" in check_ok.covered_knowledge_types

    # 2. Insufficient: Empty results
    check_empty = evaluate_evidence_sufficiency(und_base, [])
    assert check_empty.status == SufficiencyStatus.INSUFFICIENT

    # 3. Insufficient: Only obsolete source
    obs_src = DocumentSource(
        file_name="old_interlock.pdf",
        page=1,
        revision="Rev 0",
        status=DocumentStatus.OBSOLETE
    )
    res_obs = RetrievalResult(
        chunk_id="CHK-02",
        document_id="DOC-02",
        document_type="INTERLOCK",
        equipment_tag="GA-1201A",
        content="Old trip rules",
        relevance_score=0.90,
        source=obs_src
    )
    check_obs = evaluate_evidence_sufficiency(und_base, [res_obs])
    assert check_obs.status == SufficiencyStatus.INSUFFICIENT
    assert "obsolete" in check_obs.reason.lower()

    # 4. Clarification required
    und_clarify = QueryUnderstanding(
        query="What should I check?",
        intent="troubleshooting",
        equipment_tag=None,
        resolution=ResolutionMetadata(source=ResolutionSource.NONE, confidence=ResolutionConfidence.NONE),
        requires_clarification=True,
        clarification_reason="Equipment could not be determined."
    )
    check_clarify = evaluate_evidence_sufficiency(und_clarify, [])
    assert check_clarify.status == SufficiencyStatus.CLARIFICATION_REQUIRED


def test_hybrid_retriever_pipeline():
    base_dir = Path(__file__).resolve().parent.parent
    ext_dir = base_dir / "data" / "extracted"
    registry = load_documents_from_dir(ext_dir)
    retriever = HybridRetriever(registry)

    # 1. Troubleshooting query
    req = QueryRequest(query="What should I check when GA-1201A has high vibration?")
    resp = retriever.query(req, top_k=3)

    assert resp.understanding.intent == "troubleshooting"
    assert resp.understanding.equipment_tag == "GA-1201A"
    assert len(resp.results) > 0
    assert resp.sufficiency.status == SufficiencyStatus.SUFFICIENT

    # 2. Ambiguous query
    req_amb = QueryRequest(query="What should I check if there is high vibration?")
    resp_amb = retriever.query(req_amb)
    assert resp_amb.sufficiency.status == SufficiencyStatus.CLARIFICATION_REQUIRED
    assert len(resp_amb.results) == 0
