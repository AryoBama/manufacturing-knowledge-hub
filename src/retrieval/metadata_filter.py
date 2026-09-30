from typing import List, Optional
from schemas.document import DocumentChunk
from schemas.common import DocumentStatus


def filter_by_metadata(
    chunks: List[DocumentChunk],
    equipment_tag: Optional[str] = None,
    allowed_document_types: Optional[List[str]] = None,
    preferred_status: Optional[DocumentStatus] = DocumentStatus.ISSUED_FOR_OPERATION
) -> List[DocumentChunk]:
    """
    Step 1 of Retrieval: Deterministic metadata filtering
    """
    target_tag = equipment_tag.upper() if equipment_tag else None
    target_types = [t.upper() for t in allowed_document_types] if allowed_document_types else None

    filtered: List[DocumentChunk] = []
    for chunk in chunks:
        # 1. Equipment tag match
        if target_tag:
            chunk_tag = chunk.equipment_tag.upper() if chunk.equipment_tag else None
            # Allow matching tag, or plant-wide documents where tag is None
            if chunk_tag and chunk_tag != target_tag:
                continue

        # 2. Document type match
        if target_types:
            chunk_type = str(chunk.document_type).upper()
            if chunk_type not in target_types:
                continue

        filtered.append(chunk)

    # Fallback: if strictly filtered candidates is empty and target_tag is known, fallback to tag-only
    if not filtered and target_tag:
        filtered = [c for c in chunks if c.equipment_tag and c.equipment_tag.upper() == target_tag]

    return filtered
