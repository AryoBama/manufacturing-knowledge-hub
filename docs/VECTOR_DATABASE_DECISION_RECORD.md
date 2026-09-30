# Architecture Decision Record: Vector Database & Semantic Retrieval Layer
**Project**: Chandra Asri Manufacturing Knowledge Hub (CALIBER 2026 Case 1)  
**Status**: APPROVED & FROZEN  
**Phase**: VDB-0 Decision Gate  

---

## 1. Decision Summary

| Decision ID | Topic | Decision | Justification |
|---|---|---|---|
| **D1** | **Embedding Provider & Model** | `TfidfDenseEmbedder` (Local 384-dim, sublinear TF, char-wb ngrams, L2 normalized) + Pluggable `GeminiAPIEmbedder` / `OpenAIEmbedder` | Zero external dependency, 100% offline, deterministic, sub-millisecond latency, handles plant alphanumeric tags and Indonesian/English variants without hallucination or network failures. |
| **D2** | **Vector Database Engine** | `SQLiteVectorStore` (Embedded SQLite + NumPy vectorized cosine similarity) | Meets 100% of criteria: persistent storage (`data/vector_store.db`), exact SQL metadata filtering, atomic transactions, zero container/daemon overhead, easily inspectable. |
| **D3** | **Distance Metric** | **Cosine Similarity** (L2-normalized dot product) | Range [-1.0, 1.0], standard for normalized textual embeddings, unaffected by document length variations. |
| **D4** | **What Gets Embedded** | All 4 Canonical Knowledge Objects: `DocumentChunk`, `TechnicalRecord`, `RelationshipRecord`, and `MaintenanceRecord` | Ensures parameter specs, safety interlocks, and breakdown history are all semantically discoverable alongside procedures. |
| **D5** | **Chunking Strategy** | Existing Canonical Objects | Ingestion already produces semantically cohesive, bounded units. Re-chunking is avoided to preserve exact line/page/sheet traceability. |
| **D6** | **Collection Strategy** | Single Collection (`manufacturing_knowledge`) with indexed metadata filters | Eliminates multi-collection routing overhead while enabling multi-attribute filtering (asset, doc type, approval status). |
| **D7** | **Metadata Schema** | `EmbeddingDocument` with 14 strict provenance fields | Full traceability from `vector_id` back to `document_id`, `source_file`, `revision`, and `page/sheet`. |
| **D8** | **Source Eligibility** | Index all structured knowledge; filter out `DRAFT` and `OBSOLETE` during retrieval | Preserves complete plant history while strictly blocking unapproved operational guidance at retrieval time. |
| **D9** | **Revision Policy** | Content-hash driven update; `content_hash` mismatch triggers re-embedding; obsolete marked inactive | Prevents re-embedding unchanged documents; ensures only latest approved revisions answer operational queries. |
| **D10** | **Incremental Indexing** | Deterministic SHA-256 content hashing (`records_seen`, `records_indexed`, `records_skipped`, `records_updated`) | Fast synchronization without re-indexing untouched files. |
| **D11** | **Hybrid Scoring Formula** | `Score = 0.40 * Lexical + 0.20 * Fuzzy + 0.40 * Vector + Exact Tag Boost` | Balances exact tag matching (crucial for safety) with semantic concept similarity. Fully configurable via JSON. |
| **D12** | **Retrieval Strategy** | Strategy A: Parallel Retrieval (Metadata Filter -> Lexical + Fuzzy + Vector -> Hybrid Fusion) | Maximizes recall and ensures vector search cannot override authoritative metadata constraints. |
| **D13** | **Reranking** | Deterministic Hybrid Scoring | Avoids heavy cross-encoder neural dependencies while meeting 100% Hit@1 targets. |
| **D14** | **Top-K Parameters** | `vector_candidate_k = 10`, `final_evidence_k = 5` | Provides sufficient candidate diversity before hybrid filtering. |
| **D15** | **Similarity Threshold** | `semantic_candidate_threshold = 0.25` | Calibrated against technical synonym pairs and adversarial out-of-scope queries. |

---

## 2. Invariant Architecture Boundaries

1. **Vector DB is an Index, NOT the Source of Truth**: The vector store can be dropped and rebuilt from `data/extracted/` and `data/processed/` at any time.
2. **Metadata Purity**: If a document has no revision or page, the metadata remains `null`; no defaults (e.g. `Rev.00` or `Page 1`) are ever invented.
3. **Equipment Identity is Authoritative**: High semantic similarity on `GA-1201B` will **never** be served as evidence for `GA-1201A`.
