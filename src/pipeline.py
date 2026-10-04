from pathlib import Path
from typing import Optional, Dict, Any

from src.ingestion.document_loader import load_documents_from_dir, DocumentRegistry
from src.query.models import QueryRequest
from src.query.routing import understand_query
from src.retrieval.retriever import HybridRetriever
from src.retrieval.structured_store import StructuredKnowledgeStore
from src.retrieval.sufficiency import evaluate_evidence_sufficiency
from src.generation.evidence import EvidencePackage, EvidenceFusionEngine
from src.generation.models import GeneratedAnswer
from src.generation.synthesizer import AnswerSynthesizer
from src.generation.formatter import AnswerFormatter
from src.generation.llm_adapter import LLMAnswerAdapter
from src.vector import SQLiteVectorStore, TfidfDenseEmbedder, VectorIndexer
from src.failure_memory.analyzer import FailureMemoryAnalyzer
from src.graph.engine import PlantKnowledgeGraph
from src.observability.tracer import QueryTracer, QueryTraceRecord



class ManufacturingKnowledgeHub:
    """
    Unified Manufacturing Knowledge Hub Pipeline:
    Connects:
      1. Query Understanding (Entity Resolution + Intent Classification)
      2. Hybrid Document Retrieval (Lexical + Subword Cosine + Metadata Filter)
      3. Structured Store Querying (TechnicalRecords, Relationships, Maintenance)
      4. Evidence Fusion (Unifies chunks, parameters, relationships into EvidencePackage)
      5. Evidence Sufficiency Gate (Relevance + Provenance + Obsolescence Check)
      6. Answer Generation (Grounded Synthesis + Source Citations + Decoupled Actions)
    """
    def __init__(
        self,
        extracted_dir: Optional[Path] = None,
        processed_dir: Optional[Path] = None,
        use_llm: Optional[bool] = None
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.base_dir = base_dir
        self.extracted_dir = extracted_dir or (base_dir / "data" / "extracted")
        self.processed_dir = processed_dir or (base_dir / "data" / "processed")

        # 1. Load textual DocumentRegistry
        self.registry: DocumentRegistry = load_documents_from_dir(self.extracted_dir)

        # 2. Load Structured Store
        self.structured_store: StructuredKnowledgeStore = StructuredKnowledgeStore.load_from_processed_dir(self.processed_dir)

        # 3. Vector Database & Incremental Indexer (VDB Layer)
        self.vector_db_path = self.processed_dir.parent / "vector_store.db"
        self.vector_store = SQLiteVectorStore(db_path=self.vector_db_path)
        self.embedder = TfidfDenseEmbedder()
        self.indexer = VectorIndexer(vector_store=self.vector_store, embedder=self.embedder)

        # Index canonical records incrementally
        if self.vector_store.count() < 10:
            self.indexer.index(self.registry.get_all(), self.structured_store)

        # 4. Multi-Signal Hybrid Retriever (Metadata + Lexical + Subword + Vector)
        self.retriever = HybridRetriever(
            registry=self.registry,
            vector_store=self.vector_store,
            embedder=self.embedder
        )

        # 5. Synthesizer & LLM Adapter
        self.synthesizer = AnswerSynthesizer(structured_store=self.structured_store)
        self.llm_adapter = LLMAnswerAdapter(fallback_synthesizer=self.synthesizer, structured_store=self.structured_store)
        
        # Auto-enable LLM if credentials exist and OFFLINE_MODE is not true
        if use_llm is None:
            import os
            from src.adapters.llm import is_valid_api_key
            offline = os.getenv("OFFLINE_MODE", "false").lower() == "true"
            has_credentials = any(
                is_valid_api_key(os.getenv(k))
                for k in ("NVIDIA_API_KEY", "DEEPSEEK_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY")
            )
            self.use_llm = (not offline) and has_credentials
        else:
            self.use_llm = use_llm

        # 6. Active Failure Memory & Plant Knowledge Graph
        self.failure_memory = FailureMemoryAnalyzer.from_processed_dir(self.processed_dir)
        self.graph = PlantKnowledgeGraph.load_from_processed_dir(self.processed_dir)

    def get_active_equipment(self) -> list[str]:
        """Returns sorted list of active equipment tags dynamically from plant registry & stores."""
        from src.query.parser import PLANT_EQUIPMENT_REGISTRY
        tags = set(PLANT_EQUIPMENT_REGISTRY.keys())
        if self.structured_store:
            if hasattr(self.structured_store, "_tech_by_tag"):
                tags.update(self.structured_store._tech_by_tag.keys())
            elif hasattr(self.structured_store, "technical_records"):
                tags.update(tr.equipment_tag for tr in self.structured_store.technical_records if getattr(tr, "equipment_tag", None))
        return sorted(t for t in tags if t)

    def get_latest_benchmark_report(self) -> dict:
        """Loads the latest baseline evaluation report without exposing filesystem paths to caller."""
        import json
        report_file = self.base_dir / "evaluation" / "reports" / "baseline_report.json"
        if not report_file.exists():
            return {"status": "pending", "message": "Baseline report not yet generated."}
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {"status": "error", "message": f"Failed to load benchmark report: {str(e)}"}


    def build_evidence_package(
        self,
        question: str,
        session_context: Optional[Dict[str, Any]] = None,
        explicit_tag: Optional[str] = None
    ) -> EvidencePackage:
        """
        Executes Steps 1 to 4 to construct the standardized EvidencePackage.
        Allows testing and inspecting evidence packages independently of generation.
        """
        req = QueryRequest(
            query=question,
            equipment_tag=explicit_tag,
            session_context=session_context or {}
        )

        understanding = understand_query(req)
        results = self.retriever.retrieve(understanding, top_k=5)
        sufficiency = evaluate_evidence_sufficiency(understanding, results)

        return EvidenceFusionEngine.fuse(
            understanding=understanding,
            retrieval_results=results,
            sufficiency=sufficiency,
            structured_store=self.structured_store
        )

    def ask(
        self,
        question: str,
        session_context: Optional[Dict[str, Any]] = None,
        explicit_tag: Optional[str] = None
    ) -> GeneratedAnswer:
        """
        End-to-End Query-to-Answer Pipeline with stage-by-stage latency observability.
        """
        tracer = QueryTracer(query_text=question)

        # Stage 1: NLU & Understanding
        tracer.start_stage("nlu")
        req = QueryRequest(
            query=question,
            equipment_tag=explicit_tag,
            session_context=session_context or {}
        )
        understanding = understand_query(req)
        tracer.end_stage("nlu")

        # Stage 2: Hybrid Retrieval
        tracer.start_stage("retrieval")
        results = self.retriever.retrieve(understanding, top_k=5)
        tracer.end_stage("retrieval")

        # Stage 3: Sufficiency & Conflict Gate
        tracer.start_stage("sufficiency")
        sufficiency = evaluate_evidence_sufficiency(understanding, results)
        package = EvidenceFusionEngine.fuse(
            understanding=understanding,
            retrieval_results=results,
            sufficiency=sufficiency,
            structured_store=self.structured_store
        )
        tracer.end_stage("sufficiency")

        # Stage 4: Generation & Answer Synthesis
        tracer.start_stage("generation")
        if self.use_llm:
            ans = self.llm_adapter.generate(package)
        else:
            ans = self.synthesizer.generate(package)
        tracer.end_stage("generation")

        latencies = tracer.finalize()
        ans.query_id = tracer.query_id
        ans.trace = latencies

        # Log trace audit asynchronously / safely
        try:
            audit_rec = QueryTraceRecord(
                query_id=tracer.query_id,
                timestamp=latencies.timestamp,
                query_text=question,
                equipment_tag=ans.equipment_tag,
                intent=ans.intent,
                sufficiency_status=str(package.sufficiency),
                confidence_level=str(ans.confidence),
                confidence_score=ans.confidence_score,
                citations_count=len(ans.citations),
                recommendations_count=len(ans.recommendations),
                latencies=latencies
            )
            tracer.log_audit(audit_rec)
        except Exception:
            pass

        return ans


    def ask_formatted(
        self,
        question: str,
        format_type: str = "terminal",
        session_context: Optional[Dict[str, Any]] = None,
        explicit_tag: Optional[str] = None
    ) -> str:
        ans = self.ask(question, session_context=session_context, explicit_tag=explicit_tag)
        if format_type.lower() == "markdown":
            return AnswerFormatter.to_markdown(ans)
        return AnswerFormatter.to_terminal_text(ans)
