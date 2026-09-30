import hashlib
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from schemas.common import DocumentSource, DocumentStatus


def compute_content_hash(text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Computes deterministic SHA-256 content hash of text and metadata for incremental indexing.
    """
    hasher = hashlib.sha256()
    hasher.update(text.strip().encode("utf-8"))
    if metadata:
        for k in sorted(metadata.keys()):
            hasher.update(f"{k}:{metadata[k]}".encode("utf-8"))
    return hasher.hexdigest()


class EmbeddingDocument(BaseModel):
    """
    VDB-1: Standardized vector indexing contract.
    Preserves exact provenance traceability from vector_id to canonical source document.
    """
    vector_id: str = Field(..., description="Unique vector ID e.g. VEC-DOC-..., VEC-TR-...")
    record_id: str = Field(..., description="Canonical object ID (chunk_id, record_id, etc.)")
    text: str = Field(..., description="Normalized text representation embedded in vector space")
    record_type: str = Field(..., description="'document_chunk' | 'technical_parameter' | 'relationship' | 'maintenance_event'")
    equipment_tag: Optional[str] = Field(None, description="Target plant equipment tag")
    document_id: str = Field(..., description="Official document identifier")
    document_type: str = Field(..., description="DATASHEET, PID, INTERLOCK, OPL, MAINTENANCE")
    knowledge_type: Optional[str] = Field(None, description="Functional knowledge category")
    revision: Optional[str] = Field(None, description="Document revision (null if unversioned)")
    status: Optional[str] = Field(None, description="Approval status (null if unstated)")
    source: DocumentSource = Field(..., description="Complete source tracking metadata")
    content_hash: str = Field(..., description="Deterministic hash for incremental sync")
    embedding_model: str = Field(default="tfidf-dense-384", description="Model name used to embed")
    embedding_version: str = Field(default="1.0.0", description="Version of the embedding configuration")


class VectorSearchResult(BaseModel):
    """
    VDB-1: Standardized vector query output.
    Note: similarity is retrieval metadata, NOT answer confidence!
    """
    vector_id: str
    record_id: str
    similarity: float = Field(..., description="Cosine similarity score [-1.0, 1.0]")
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: DocumentSource


class IndexReport(BaseModel):
    """
    VDB-1: Observability report emitted after every indexer synchronization run.
    """
    records_seen: int = 0
    records_indexed: int = 0
    records_skipped: int = 0
    records_updated: int = 0
    records_deactivated: int = 0
    embedding_errors: int = 0
    validation_errors: int = 0
    embedding_model: str = ""
    embedding_version: str = ""


class VectorStore(ABC):
    """
    VDB-1: Vendor-neutral vector database interface.
    """
    @abstractmethod
    def upsert(self, documents: List[EmbeddingDocument], embeddings: List[List[float]]) -> int:
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        pass

    @abstractmethod
    def get_by_id(self, vector_id: str) -> Optional[EmbeddingDocument]:
        pass

    @abstractmethod
    def delete(self, vector_ids: List[str]) -> int:
        pass

    @abstractmethod
    def count(self) -> int:
        pass
