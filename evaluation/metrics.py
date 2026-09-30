from typing import List, Optional, Set, Dict, Any
import re


def calculate_accuracy(correct_count: int, total_count: int) -> float:
    """Calculates percentage accuracy [0.0 - 100.0]."""
    if total_count == 0:
        return 0.0
    return round((correct_count / total_count) * 100.0, 2)


def calculate_mrr(ranks: List[int]) -> float:
    """
    Calculates Mean Reciprocal Rank (MRR).
    ranks: 1-indexed rank of first relevant item (or 0 / None if not found).
    """
    if not ranks:
        return 0.0
    reciprocal_sum = sum(1.0 / r for r in ranks if r > 0)
    return round(reciprocal_sum / len(ranks), 4)


def hit_at_k(retrieved_ids: List[str], target_id: str, k: int) -> bool:
    """Returns True if target_id is present within the top-k retrieved IDs."""
    if not target_id or not retrieved_ids:
        return False
    target_clean = target_id.strip().upper()
    top_k_candidates = [cid.strip().upper() for cid in retrieved_ids[:k]]
    return any(target_clean in cand or cand in target_clean for cand in top_k_candidates)


def verify_numeric_presence(text: str, expected_numbers: List[str], expected_units: Optional[List[str]] = None) -> bool:
    """
    Verifies that expected numbers (e.g. '45', '120') and units (e.g. 'm3/h', 'm')
    are preserved accurately in generated text without distortion.
    """
    if not text:
        return False
    lower_text = text.lower()
    for num in expected_numbers:
        if num not in lower_text:
            return False
    if expected_units:
        for unit in expected_units:
            norm_unit = unit.lower().replace("³", "3").replace("degc", "c").replace("°c", "c")
            norm_text = lower_text.replace("³", "3").replace("degc", "c").replace("°c", "c")
            if norm_unit not in norm_text:
                return False
    return True


def verify_citation_integrity(citations: List[Any], expected_doc_id: Optional[str] = None, expected_doc_type: Optional[str] = None) -> bool:
    """
    Verifies that citations have stable evidence_id, correct doc_id, and non-empty metadata.
    """
    if not citations:
        return False
    for c in citations:
        # Every citation must have a stable evidence_id and document_id
        ev_id = getattr(c, "evidence_id", "")
        doc_id = getattr(c, "document_id", "")
        doc_type = getattr(c, "document_type", "")
        if not ev_id or not doc_id:
            return False
        if expected_doc_id and (expected_doc_id.upper() in doc_id.upper() or doc_id.upper() in expected_doc_id.upper()):
            return True
        if expected_doc_type and expected_doc_type.upper() == doc_type.upper():
            return True
    return False if (expected_doc_id or expected_doc_type) else True
