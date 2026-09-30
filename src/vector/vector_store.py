import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np

from schemas.common import DocumentSource, DocumentStatus
from src.vector.models import VectorStore, EmbeddingDocument, VectorSearchResult


class SQLiteVectorStore(VectorStore):
    """
    VDB-3: Persistent SQLite Vector Database with NumPy Cosine Similarity.
    Provides atomic transactions, indexed metadata filtering, persistent disk storage,
    and zero daemon/container dependencies.
    """
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path) if db_path else ":memory:"
        if db_path and str(db_path) != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(db_path))
        else:
            self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return self._conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                vector_id TEXT PRIMARY KEY,
                record_id TEXT NOT NULL,
                text TEXT NOT NULL,
                record_type TEXT NOT NULL,
                equipment_tag TEXT,
                document_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                knowledge_type TEXT,
                revision TEXT,
                status TEXT,
                file_name TEXT NOT NULL,
                page INTEGER,
                sheet TEXT,
                content_hash TEXT NOT NULL,
                embedding_model TEXT NOT NULL,
                embedding_version TEXT NOT NULL,
                embedding BLOB NOT NULL,
                is_active INTEGER DEFAULT 1
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tag ON vectors (equipment_tag);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_type ON vectors (document_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_id ON vectors (document_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON vectors (content_hash);")
            conn.commit()

    def upsert(self, documents: List[EmbeddingDocument], embeddings: List[List[float]]) -> int:
        if len(documents) != len(embeddings):
            raise ValueError(f"Documents count ({len(documents)}) != embeddings count ({len(embeddings)})")

        with self._get_connection() as conn:
            for doc, emb in zip(documents, embeddings):
                blob = np.array(emb, dtype=np.float32).tobytes()
                conn.execute("""
                INSERT OR REPLACE INTO vectors (
                    vector_id, record_id, text, record_type, equipment_tag,
                    document_id, document_type, knowledge_type, revision, status,
                    file_name, page, sheet, content_hash, embedding_model,
                    embedding_version, embedding, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    doc.vector_id, doc.record_id, doc.text, doc.record_type,
                    doc.equipment_tag.upper() if doc.equipment_tag else None,
                    doc.document_id, doc.document_type, doc.knowledge_type,
                    doc.revision, doc.status, doc.source.file_name,
                    doc.source.page, doc.source.sheet, doc.content_hash,
                    doc.embedding_model, doc.embedding_version, blob
                ))
            conn.commit()
        return len(documents)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        flt = filters or {}
        clauses = ["is_active = 1"]
        params = []

        # 1. Authoritative Equipment Tag filter
        target_tag = flt.get("equipment_tag")
        if target_tag:
            clauses.append("(equipment_tag = ? OR equipment_tag IS NULL)")
            params.append(target_tag.upper())

        # 2. Document Type filter
        doc_types = flt.get("document_types")
        if doc_types:
            placeholders = ",".join("?" for _ in doc_types)
            clauses.append(f"document_type IN ({placeholders})")
            params.extend([d.upper() for d in doc_types])

        # 3. Status Eligibility filter (exclude draft/obsolete by default)
        exclude_statuses = flt.get("exclude_statuses", ["Draft", "Obsolete"])
        if exclude_statuses:
            placeholders = ",".join("?" for _ in exclude_statuses)
            clauses.append(f"(status NOT IN ({placeholders}) OR status IS NULL)")
            params.extend(exclude_statuses)

        where_clause = " AND ".join(clauses)
        sql = f"SELECT * FROM vectors WHERE {where_clause}"

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        if not rows:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []
        q_vec = q_vec / q_norm

        results = []
        for r in rows:
            vec = np.frombuffer(r["embedding"], dtype=np.float32)
            norm = np.linalg.norm(vec)
            sim = float(np.dot(vec, q_vec) / (norm * q_norm)) if norm > 0 else 0.0

            src = DocumentSource(
                file_name=r["file_name"],
                page=r["page"] if r["page"] is not None else 1,
                sheet=r["sheet"],
                revision=r["revision"],
                status=DocumentStatus(r["status"]) if r["status"] in DocumentStatus._value2member_map_ else None
            )

            results.append(
                VectorSearchResult(
                    vector_id=r["vector_id"],
                    record_id=r["record_id"],
                    similarity=round(sim, 4),
                    content=r["text"],
                    metadata={
                        "record_type": r["record_type"],
                        "equipment_tag": r["equipment_tag"],
                        "document_id": r["document_id"],
                        "document_type": r["document_type"],
                        "knowledge_type": r["knowledge_type"]
                    },
                    source=src
                )
            )

        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]

    def get_by_id(self, vector_id: str) -> Optional[EmbeddingDocument]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM vectors WHERE vector_id = ?", (vector_id,)).fetchone()
            if not row:
                return None
            src = DocumentSource(
                file_name=row["file_name"],
                page=row["page"] if row["page"] is not None else 1,
                sheet=row["sheet"],
                revision=row["revision"],
                status=DocumentStatus(row["status"]) if row["status"] in DocumentStatus._value2member_map_ else None
            )
            return EmbeddingDocument(
                vector_id=row["vector_id"],
                record_id=row["record_id"],
                text=row["text"],
                record_type=row["record_type"],
                equipment_tag=row["equipment_tag"],
                document_id=row["document_id"],
                document_type=row["document_type"],
                knowledge_type=row["knowledge_type"],
                revision=row["revision"],
                status=row["status"],
                source=src,
                content_hash=row["content_hash"],
                embedding_model=row["embedding_model"],
                embedding_version=row["embedding_version"]
            )

    def delete(self, vector_ids: List[str]) -> int:
        if not vector_ids:
            return 0
        with self._get_connection() as conn:
            placeholders = ",".join("?" for _ in vector_ids)
            cur = conn.execute(f"UPDATE vectors SET is_active = 0 WHERE vector_id IN ({placeholders})", vector_ids)
            conn.commit()
            return cur.rowcount

    def count(self) -> int:
        with self._get_connection() as conn:
            res = conn.execute("SELECT COUNT(*) FROM vectors WHERE is_active = 1").fetchone()
            return res[0] if res else 0
