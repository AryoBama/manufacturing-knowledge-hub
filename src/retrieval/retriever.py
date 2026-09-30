from typing import List, Optional, Dict, Any

from src.query.models import QueryUnderstanding, QueryRequest
from src.query.routing import understand_query, route_knowledge_to_documents
from src.retrieval.models import RetrievalResult, RetrievalResponse
from src.retrieval.metadata_filter import filter_by_metadata
from src.retrieval.lexical import compute_lexical_score
from src.retrieval.semantic import compute_fuzzy_subword_score
from src.retrieval.sufficiency import evaluate_evidence_sufficiency
from src.ingestion.document_loader import DocumentRegistry
from src.vector.models import VectorStore
from src.vector.embedder import EmbeddingProvider
from src.vector.semantic_retriever import SemanticRetriever


import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "configs" / "retrieval_config.json"
_DEFAULT_WEIGHTS = {"lexical_weight": 0.40, "fuzzy_weight": 0.20, "vector_weight": 0.40, "top_k": 5}
if _CONFIG_PATH.exists():
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
            _cfg = json.load(_f).get("retrieval", {})
            _DEFAULT_WEIGHTS.update(_cfg)
    except Exception:
        pass


class HybridRetriever:
    """
    VDB-7: Hardened Multi-Signal Industrial Hybrid Retrieval Engine.
    Combines:
      1. Deterministic Metadata Pre-Filtering (Authoritative Asset & Document Isolation)
      2. Lexical Terminology Search (Exact Keyword & Setpoint Boost)
      3. Character-Level Subword Matching (Morphological Variants & Typos)
      4. Dense Vector Semantic Retrieval (Embedding Similarity)
    With automatic graceful fallback if Vector Database is unavailable.
    Weights are configurable via configs/retrieval_config.json.
    """
    def __init__(
        self,
        registry: DocumentRegistry,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[EmbeddingProvider] = None,
        lexical_weight: Optional[float] = None,
        fuzzy_weight: Optional[float] = None,
        vector_weight: Optional[float] = None
    ):
        self.registry = registry
        self.vector_store = vector_store
        self.embedder = embedder
        self.semantic_retriever = SemanticRetriever(vector_store, embedder) if vector_store else None

        self.lexical_weight = lexical_weight if lexical_weight is not None else _DEFAULT_WEIGHTS["lexical_weight"]
        self.fuzzy_weight = fuzzy_weight if fuzzy_weight is not None else _DEFAULT_WEIGHTS["fuzzy_weight"]
        self.vector_weight = vector_weight if vector_weight is not None else _DEFAULT_WEIGHTS["vector_weight"]

    def retrieve(
        self,
        understanding: QueryUnderstanding,
        top_k: int = _DEFAULT_WEIGHTS.get("top_k", 5)
    ) -> List[RetrievalResult]:
        if understanding.requires_clarification:
            return []

        all_chunks = self.registry.get_all()

        # Step 1: Metadata Filtering (Intent-Specific Source Priority)
        target_doc_types = route_knowledge_to_documents(
            understanding.knowledge_types,
            intent=understanding.intent
        )
        candidates = filter_by_metadata(
            chunks=all_chunks,
            equipment_tag=understanding.equipment_tag,
            allowed_document_types=target_doc_types
        )

        if not candidates:
            return []

        # Step 2: Vector Semantic Retrieval (if VectorStore active)
        vector_sim_map: Dict[str, float] = {}
        if self.semantic_retriever:
            try:
                v_results = self.semantic_retriever.search(
                    query=understanding.query,
                    equipment_tag=understanding.equipment_tag,
                    document_types=target_doc_types,
                    top_k=20,
                    similarity_threshold=0.0
                )
                for vr in v_results:
                    vector_sim_map[vr.record_id] = vr.similarity
            except Exception:
                # Graceful fallback: continue without vector scores if DB unavailable
                vector_sim_map = {}

        # Step 3: Multi-Signal Scoring
        scored_results: List[RetrievalResult] = []
        target_tag = understanding.equipment_tag

        for chunk in candidates:
            lex_score = compute_lexical_score(understanding.query, chunk.content, target_tag)
            subword_score = compute_fuzzy_subword_score(understanding.query, chunk.content)

            # Step 4: Weighted Hybrid Ranking
            if vector_sim_map:
                vec_score = vector_sim_map.get(chunk.chunk_id, 0.0)
                # Normalize vec_score to [0, 1] range
                vec_norm = max(0.0, min(1.0, vec_score))
                combined_score = round(
                    self.lexical_weight * lex_score +
                    self.fuzzy_weight * subword_score +
                    self.vector_weight * vec_norm,
                    4
                )
            else:
                # Fallback to 50/50 lexical + fuzzy
                combined_score = round(0.5 * lex_score + 0.5 * subword_score, 4)

            scored_results.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_type=str(chunk.document_type),
                    equipment_tag=chunk.equipment_tag,
                    content=chunk.content,
                    relevance_score=combined_score,
                    source=chunk.source
                )
            )

        # Step 5: Rank and return top-K
        scored_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored_results[:top_k]

    def query(self, request: QueryRequest, top_k: int = 5) -> RetrievalResponse:
        understanding = understand_query(request)
        results = self.retrieve(understanding, top_k=top_k)
        sufficiency = evaluate_evidence_sufficiency(understanding, results)

        return RetrievalResponse(
            query=request.query,
            understanding=understanding,
            results=results,
            sufficiency=sufficiency
        )
