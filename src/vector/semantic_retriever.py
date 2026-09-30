from typing import List, Optional, Dict, Any

from src.vector.models import VectorStore, VectorSearchResult
from src.vector.embedder import EmbeddingProvider, TfidfDenseEmbedder


class SemanticRetriever:
    """
    VDB-6: Dedicated Semantic Vector Search Retriever.
    Embeds natural-language queries, applies strict metadata pre-filters,
    and returns ranked VectorSearchResults with similarity scores.
    """
    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Optional[EmbeddingProvider] = None
    ):
        self.vector_store = vector_store
        self.embedder = embedder or TfidfDenseEmbedder()

    def search(
        self,
        query: str,
        equipment_tag: Optional[str] = None,
        document_types: Optional[List[str]] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.15
    ) -> List[VectorSearchResult]:
        if not query.strip():
            return []

        q_vec = self.embedder.embed_text(query)

        filters: Dict[str, Any] = {}
        if equipment_tag:
            filters["equipment_tag"] = equipment_tag
        if document_types:
            filters["document_types"] = document_types

        results = self.vector_store.search(
            query_embedding=q_vec,
            top_k=top_k,
            filters=filters
        )

        return [r for r in results if r.similarity >= similarity_threshold]
