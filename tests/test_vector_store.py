import pytest
import numpy as np
from pathlib import Path

from schemas.common import DocumentSource, DocumentStatus
from schemas.document import DocumentChunk
from src.vector.models import EmbeddingDocument, compute_content_hash
from src.vector.embedder import TfidfDenseEmbedder
from src.vector.vector_store import SQLiteVectorStore
from src.vector.indexer import VectorIndexer
from src.vector.semantic_retriever import SemanticRetriever


@pytest.fixture
def vector_store():
    return SQLiteVectorStore(":memory:")


@pytest.fixture
def embedder():
    return TfidfDenseEmbedder(dimension=384)


def test_embedder_dimension_and_norm(embedder):
    vec = embedder.embed_text("What is GA-1201A rated flow?")
    assert len(vec) == 384
    norm = np.linalg.norm(vec)
    assert pytest.approx(norm, rel=1e-3) == 1.0


def test_vector_store_upsert_and_search(vector_store, embedder):
    src = DocumentSource(file_name="datasheet.pdf", page=1, revision="Rev 3", status=DocumentStatus.APPROVED)
    doc1 = EmbeddingDocument(
        vector_id="VEC-DOC-001",
        record_id="CHK-001",
        text="GA-1201A rated flow is 45 m3/h with differential pressure 8.6 bar",
        record_type="document_chunk",
        equipment_tag="GA-1201A",
        document_id="DS-001",
        document_type="DATASHEET",
        revision="Rev 3",
        status="Approved",
        source=src,
        content_hash="hash1"
    )
    doc2 = EmbeddingDocument(
        vector_id="VEC-DOC-002",
        record_id="CHK-002",
        text="KC-4501 recycle gas compressor vibration trip limit 7.1 mm/s",
        record_type="document_chunk",
        equipment_tag="KC-4501",
        document_id="IL-001",
        document_type="INTERLOCK",
        revision="Rev 1",
        status="Approved",
        source=src,
        content_hash="hash2"
    )

    embs = embedder.embed_batch([doc1.text, doc2.text])
    count = vector_store.upsert([doc1, doc2], embs)
    assert count == 2
    assert vector_store.count() == 2

    # Query matching doc1
    q_vec = embedder.embed_text("rated flow of pump")
    results = vector_store.search(q_vec, top_k=5)
    assert len(results) >= 1
    assert results[0].record_id == "CHK-001"
    assert results[0].similarity > 0.1

    # Metadata filtering by equipment_tag
    filtered = vector_store.search(q_vec, top_k=5, filters={"equipment_tag": "KC-4501"})
    assert len(filtered) == 1
    assert filtered[0].record_id == "CHK-002"


def test_vector_indexer_incremental_sync(vector_store, embedder):
    indexer = VectorIndexer(vector_store, embedder)
    src = DocumentSource(file_name="test.pdf", page=1, revision="Rev 1", status=DocumentStatus.APPROVED)
    chunk = DocumentChunk(
        chunk_id="DOC-01-P01-C01",
        document_id="DOC-01",
        document_type="DATASHEET",
        title="Test Chunk",
        equipment_tag="GA-1201A",
        content="Centrifugal pump rated capacity 45 cubic meters per hour",
        source=src
    )

    # First run: 1 indexed
    rep1 = indexer.index([chunk])
    assert rep1.records_seen == 1
    assert rep1.records_indexed == 1
    assert rep1.records_skipped == 0
    assert vector_store.count() == 1

    # Second run with same content: 1 skipped (incremental sync!)
    rep2 = indexer.index([chunk])
    assert rep2.records_seen == 1
    assert rep2.records_indexed == 0
    assert rep2.records_skipped == 1


def test_authoritative_equipment_filtering_rejects_cross_asset(vector_store, embedder):
    src = DocumentSource(file_name="test.pdf", page=1, revision="Rev 1", status=DocumentStatus.APPROVED)
    doc_a = EmbeddingDocument(
        vector_id="VEC-A",
        record_id="CHK-A",
        text="High vibration alarm triggers on pump GA-1201A",
        record_type="document_chunk",
        equipment_tag="GA-1201A",
        document_id="DOC-A",
        document_type="OPL",
        source=src,
        content_hash="hA"
    )
    doc_b = EmbeddingDocument(
        vector_id="VEC-B",
        record_id="CHK-B",
        text="High vibration alarm triggers on pump GA-1201B",
        record_type="document_chunk",
        equipment_tag="GA-1201B",
        document_id="DOC-B",
        document_type="OPL",
        source=src,
        content_hash="hB"
    )
    vector_store.upsert([doc_a, doc_b], embedder.embed_batch([doc_a.text, doc_b.text]))

    sr = SemanticRetriever(vector_store, embedder)
    # Query specifying GA-1201A MUST NOT return GA-1201B
    res = sr.search("vibration alarm", equipment_tag="GA-1201A")
    assert all(r.metadata["equipment_tag"] == "GA-1201A" for r in res)
