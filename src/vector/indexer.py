from pathlib import Path
from typing import List, Optional, Dict, Any

from schemas.common import DocumentSource, DocumentStatus
from schemas.document import DocumentChunk
from schemas.technical import TechnicalRecord
from schemas.relationship import RelationshipRecord
from schemas.maintenance import MaintenanceRecord
from src.ingestion.document_loader import load_documents_from_dir
from src.retrieval.structured_store import StructuredKnowledgeStore
from src.vector.models import EmbeddingDocument, IndexReport, compute_content_hash, VectorStore
from src.vector.embedder import EmbeddingProvider, TfidfDenseEmbedder


class VectorIndexer:
    """
    VDB-4: Deterministic Incremental Vector Indexer.
    Extracts canonical objects, constructs factual natural-language representations,
    detects changes via content hashing, generates embeddings, and updates VectorStore.
    """
    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Optional[EmbeddingProvider] = None
    ):
        self.vector_store = vector_store
        self.embedder = embedder or TfidfDenseEmbedder()

    def build_embedding_documents(
        self,
        chunks: List[DocumentChunk],
        structured_store: Optional[StructuredKnowledgeStore] = None
    ) -> List[EmbeddingDocument]:
        docs: List[EmbeddingDocument] = []

        # 1. Document Chunks
        for c in chunks:
            h = compute_content_hash(c.content, {"doc_id": c.document_id, "rev": c.source.revision})
            stat_val = c.source.status.value if hasattr(c.source.status, "value") else str(c.source.status or "")
            docs.append(
                EmbeddingDocument(
                    vector_id=f"VEC-DOC-{c.chunk_id}",
                    record_id=c.chunk_id,
                    text=c.content,
                    record_type="document_chunk",
                    equipment_tag=c.equipment_tag,
                    document_id=c.document_id,
                    document_type=str(c.document_type),
                    knowledge_type=None,
                    revision=c.source.revision,
                    status=stat_val or None,
                    source=c.source,
                    content_hash=h,
                    embedding_model=self.embedder.model_name,
                    embedding_version="1.0.0"
                )
            )

        # 2. Structured Knowledge if provided
        if structured_store:
            # A. Technical Records
            for tr in structured_store.technical_records:
                text = (
                    f"Equipment: {tr.equipment_tag}. "
                    f"Category: {tr.category}. "
                    f"Parameter: {tr.parameter}. "
                    f"Value: {tr.value} {tr.unit or ''}. "
                    f"Document: {tr.document_id}."
                )
                h = compute_content_hash(text, {"rec_id": tr.record_id})
                stat_val = tr.source.status.value if hasattr(tr.source.status, "value") else str(tr.source.status or "")
                docs.append(
                    EmbeddingDocument(
                        vector_id=f"VEC-TR-{tr.record_id}",
                        record_id=tr.record_id,
                        text=text,
                        record_type="technical_parameter",
                        equipment_tag=tr.equipment_tag,
                        document_id=tr.document_id,
                        document_type=str(tr.document_type),
                        knowledge_type="equipment_spec",
                        revision=tr.source.revision,
                        status=stat_val or None,
                        source=tr.source,
                        content_hash=h,
                        embedding_model=self.embedder.model_name,
                        embedding_version="1.0.0"
                    )
                )

            # B. Relationship Records
            for rel in structured_store.relationships:
                text = (
                    f"Equipment: {rel.equipment_tag or rel.target_tag}. "
                    f"Instrument: {rel.source_tag}. "
                    f"Relationship: {rel.relationship}. "
                    f"Target: {rel.target_tag}. "
                    f"Safety Logic Context: {rel.context or 'Interlock'}. "
                    f"Document: {rel.document_id}."
                )
                h = compute_content_hash(text, {"rel_id": rel.relationship_id})
                stat_val = rel.source.status.value if hasattr(rel.source.status, "value") else str(rel.source.status or "")
                docs.append(
                    EmbeddingDocument(
                        vector_id=f"VEC-REL-{rel.relationship_id}",
                        record_id=rel.relationship_id,
                        text=text,
                        record_type="relationship",
                        equipment_tag=rel.equipment_tag or rel.target_tag,
                        document_id=rel.document_id,
                        document_type=str(rel.document_type),
                        knowledge_type="protection_logic",
                        revision=rel.source.revision,
                        status=stat_val or None,
                        source=rel.source,
                        content_hash=h,
                        embedding_model=self.embedder.model_name,
                        embedding_version="1.0.0"
                    )
                )

            # C. Maintenance Records
            for mr in structured_store.maintenance_records:
                text = (
                    f"Equipment: {mr.equipment_tag}. "
                    f"Work Order Event: {mr.event_id} ({mr.date}). "
                    f"Failure Mode: {mr.failure_mode or 'None (Routine)'}. "
                    f"Downtime: {mr.downtime_hours} hours. "
                    f"Root Cause: {mr.root_cause or 'N/A'}. "
                    f"Corrective Action: {mr.corrective_action or 'N/A'}."
                )
                h = compute_content_hash(text, {"event_id": mr.event_id})
                stat_val = mr.source.status.value if hasattr(mr.source.status, "value") else str(mr.source.status or "")
                docs.append(
                    EmbeddingDocument(
                        vector_id=f"VEC-MNT-{mr.event_id}",
                        record_id=mr.event_id,
                        text=text,
                        record_type="maintenance_event",
                        equipment_tag=mr.equipment_tag,
                        document_id=mr.document_id,
                        document_type=str(mr.document_type),
                        knowledge_type="failure_history",
                        revision=mr.source.revision,
                        status=stat_val or None,
                        source=mr.source,
                        content_hash=h,
                        embedding_model=self.embedder.model_name,
                        embedding_version="1.0.0"
                    )
                )

        return docs

    def index(
        self,
        chunks: List[DocumentChunk],
        structured_store: Optional[StructuredKnowledgeStore] = None
    ) -> IndexReport:
        all_docs = self.build_embedding_documents(chunks, structured_store)
        report = IndexReport(
            records_seen=len(all_docs),
            embedding_model=self.embedder.model_name,
            embedding_version="1.0.0"
        )

        docs_to_embed: List[EmbeddingDocument] = []

        for doc in all_docs:
            existing = self.vector_store.get_by_id(doc.vector_id)
            if existing is None:
                docs_to_embed.append(doc)
                report.records_indexed += 1
            elif existing.content_hash != doc.content_hash:
                docs_to_embed.append(doc)
                report.records_updated += 1
            else:
                report.records_skipped += 1

        if docs_to_embed:
            texts = [d.text for d in docs_to_embed]
            embeddings = self.embedder.embed_batch(texts)
            self.vector_store.upsert(docs_to_embed, embeddings)

        return report
