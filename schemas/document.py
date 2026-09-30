from typing import Optional, Union, Dict, Any
from pydantic import Field, model_validator

from schemas.common import CanonicalKnowledgeBase, DocumentSource, DocumentType


class DocumentChunk(CanonicalKnowledgeBase):
    """
    1A. DocumentChunk:
    For narrative, textual, and procedural knowledge (OPL, SOP, Plot Plan narrative, general technical notes).
    """
    chunk_id: str = Field(
        ...,
        description="Structured chunk ID following rule: <document_id>-P<page>-C<index>, e.g. OPL-GA1201A-P01-C01"
    )
    title: str = Field(..., description="Title of document or section")
    equipment_type: Optional[str] = Field(None, description="Equipment category, e.g. Centrifugal Pump")
    content: str = Field(..., min_length=10, description="Standalone technical text content for AI RAG")

    @model_validator(mode="after")
    def verify_traceability_invariant(self):
        # Invariant: chunk_id must incorporate document_id for deterministic traceability
        if not self.chunk_id.startswith(self.document_id):
            raise ValueError(
                f"chunk_id '{self.chunk_id}' violates ID rule. Must start with document_id '{self.document_id}' "
                f"(recommended format: '{self.document_id}-P{self.source.page:02d}-C01')"
            )
        return self
