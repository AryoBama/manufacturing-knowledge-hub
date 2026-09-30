from typing import List, Dict, Any, Optional
from pathlib import Path

from schemas.common import DocumentSource, DocumentStatus, DocumentType
from schemas.document import DocumentChunk
from src.ingestion.metadata import normalize_revision, normalize_status, resolve_equipment


def normalize_generic_document(
    data: Dict[str, Any],
    source_metadata: Optional[DocumentSource] = None
) -> List[DocumentChunk]:
    """
    Fallback normalizer for general documents, SOPs, and technical narratives.
    """
    tag = data.get("equipment_tag")
    if tag:
        res = resolve_equipment(tag)
        if res.get("status") == "resolved":
            tag = res["equipment_tag"]

    doc_id = data.get("document_id") or data.get("doc_no", "DOC-GEN")
    title = data.get("title", "Technical Document")
    content = data.get("content", "")
    doc_type = data.get("document_type", DocumentType.OTHER)

    src = source_metadata
    if not src:
        src = DocumentSource(
            file_name=data.get("file_name", "document.pdf"),
            page=int(data.get("page", 1)),
            revision=normalize_revision(data.get("revision")),
            status=normalize_status(data.get("status")) or DocumentStatus.APPROVED
        )

    chunk = DocumentChunk(
        chunk_id=f"{doc_id}-P{src.page:02d}-C01",
        document_id=doc_id,
        document_type=doc_type,
        title=title,
        equipment_tag=tag,
        content=content if len(content) >= 10 else f"{title}: {content or 'No text provided'}",
        source=src,
        metadata=data.get("metadata", {})
    )
    return [chunk]
