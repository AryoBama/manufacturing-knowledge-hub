import json
from pathlib import Path
from typing import List, Optional
from schemas.common import DocumentStatus
from src.query.models import QueryUnderstanding
from src.query.routing import KNOWLEDGE_TO_DOCUMENTS
from src.retrieval.models import RetrievalResult, SufficiencyCheck, SufficiencyStatus

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "configs" / "retrieval_config.json"
_DEFAULT_THRESHOLD = 0.20
if _CONFIG_PATH.exists():
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
            _DEFAULT_THRESHOLD = float(json.load(_f).get("sufficiency", {}).get("min_relevance_threshold", 0.20))
    except Exception:
        pass


def evaluate_evidence_sufficiency(
    understanding: QueryUnderstanding,
    results: List[RetrievalResult],
    min_relevance_threshold: Optional[float] = None
) -> SufficiencyCheck:
    effective_threshold = min_relevance_threshold if min_relevance_threshold is not None else _DEFAULT_THRESHOLD
    """
    Phase 2F Evidence Sufficiency Checkpoint:
    Evaluates Relevance + Source Validity + Asset Match + Knowledge Coverage
    before sending context to downstream RAG answer generation.
    """
    # 0. Prompt Injection / Policy Bypass Check
    from src.query.intent import is_jailbreak_or_prompt_injection
    if is_jailbreak_or_prompt_injection(understanding.query):
        return SufficiencyCheck(
            status=SufficiencyStatus.OUT_OF_SCOPE,
            reason="Prompt injection / policy bypass attempt detected. The system strictly adheres to evidence-bounding and approved engineering documentation. Ungrounded or speculative answers are strictly prohibited."
        )

    # 1. Clarification Check
    if understanding.requires_clarification:
        return SufficiencyCheck(
            status=SufficiencyStatus.CLARIFICATION_REQUIRED,
            reason=understanding.clarification_reason or "Equipment identity needs clarification."
        )

    # 2. Results Emptiness Check
    if not results:
        target = understanding.equipment_tag or "query"
        return SufficiencyCheck(
            status=SufficiencyStatus.INSUFFICIENT,
            reason=f"No engineering documentation found for {target}."
        )

    # 3. Source Validity Check (exclude Obsolete / Draft docs from counting as approved evidence)
    valid_results = [
        r for r in results
        if r.source.status not in (DocumentStatus.OBSOLETE, DocumentStatus.DRAFT)
    ]
    if not valid_results:
        return SufficiencyCheck(
            status=SufficiencyStatus.INSUFFICIENT,
            reason="Only draft or obsolete documentation found. Verified operational evidence is required."
        )

    # 4. Relevance Threshold Check
    top_score = max(r.relevance_score for r in valid_results)
    if top_score < effective_threshold:
        return SufficiencyCheck(
            status=SufficiencyStatus.INSUFFICIENT,
            reason=f"Top candidate relevance ({top_score:.2f}) is below minimum confidence threshold ({effective_threshold})."
        )

    # 5. Asset Match Check
    target_tag = understanding.equipment_tag.upper() if understanding.equipment_tag else None
    if target_tag:
        has_asset_match = any(
            r.equipment_tag and r.equipment_tag.upper() == target_tag
            for r in valid_results
        )
        if not has_asset_match:
            return SufficiencyCheck(
                status=SufficiencyStatus.INSUFFICIENT,
                reason=f"Retrieved documentation does not directly match target asset {target_tag}."
            )

    # 6. Knowledge Coverage Analysis
    retrieved_doc_types = {r.document_type.upper() for r in valid_results}
    covered = []
    uncovered = []

    for kt in understanding.knowledge_types:
        expected_docs = {d.upper() for d in KNOWLEDGE_TO_DOCUMENTS.get(kt, [])}
        if retrieved_doc_types & expected_docs:
            covered.append(kt)
        else:
            uncovered.append(kt)

    doc_types_str = ", ".join(sorted(retrieved_doc_types))
    tag_str = f" for {target_tag}" if target_tag else ""

    # 7. Conflict Detection Check
    from src.retrieval.conflict import ConflictDetector
    conflicts = ConflictDetector.detect_conflicts(valid_results, target_tag)
    unresolved_conflicts = [c for c in conflicts if c.resolution_status == "UNRESOLVED"]

    if unresolved_conflicts:
        return SufficiencyCheck(
            status=SufficiencyStatus.CONFLICTING_EVIDENCE,
            reason=f"Conflicting engineering evidence detected across {len(unresolved_conflicts)} parameter(s).",
            covered_knowledge_types=covered,
            uncovered_knowledge_types=uncovered,
            conflicts=conflicts
        )

    return SufficiencyCheck(
        status=SufficiencyStatus.SUFFICIENT,
        reason=f"Relevant approved evidence found ({doc_types_str}){tag_str}.",
        covered_knowledge_types=covered,
        uncovered_knowledge_types=uncovered,
        conflicts=conflicts
    )

