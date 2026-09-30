from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNVERIFIED = "UNVERIFIED"


class SourceCitation(BaseModel):
    """
    Evidence-grounded citation model.
    Never defaults page to 1 or revision to Rev.00. Missing fields stay None.
    """
    evidence_id: str = Field(..., description="Unique evidence ID cited (e.g. EV-DOC-..., EV-TR-...)")
    document_id: str = Field(..., description="Official document identifier")
    document_type: str = Field(..., description="Canonical document type (DATASHEET, PID, INTERLOCK, OPL, MAINTENANCE)")
    file_name: str = Field(..., description="Original filename")
    revision: Optional[str] = Field(None, description="Document revision string (null if unknown)")
    status: Optional[str] = Field(None, description="Document approval status (null if unknown)")
    page: Optional[int] = Field(None, description="Document page number (null if not page-based)")
    sheet: Optional[str] = Field(None, description="Workbook sheet name (null if not tabular)")
    excerpt: Optional[str] = Field(None, description="Specific factual excerpt cited")

    @property
    def badge(self) -> str:
        rev_str = f" | {self.revision}" if self.revision else ""
        stat_str = f" | {self.status}" if self.status else ""
        pg_str = f" | P.{self.page}" if self.page is not None else ""
        return f"[{self.document_type}: {self.document_id}{rev_str}{stat_str}{pg_str}]"


class OperationalRecommendation(BaseModel):
    """
    Decoupled operational guidance.
    Only generated when explicit evidence or validated rules support it.
    """
    action: str = Field(..., description="Specific operational task to perform")
    basis: str = Field(..., description="Technical rationale grounded in evidence")
    evidence_id: Optional[str] = Field(None, description="Referenced evidence ID supporting this action")
    priority: str = Field(default="MEDIUM", description="CRITICAL | HIGH | MEDIUM | LOW")
    applicability: Optional[str] = Field(None, description="Operating condition under which this applies")

    # Compatibility alias
    @property
    def description(self) -> str:
        return self.action

    @property
    def action_type(self) -> str:
        return self.priority


# Compatibility alias
ActionRecommendation = OperationalRecommendation


class ConfidenceBreakdown(BaseModel):
    """
    Transparent mathematical decomposition of confidence score.
    Confidence = f(Asset, Source, Sufficiency, Coverage, Intent) - Penalties
    """
    asset_match_score: float = Field(..., description="Weight: 25%. Precision of equipment entity resolution (0.0 to 1.0)")
    source_validity_score: float = Field(..., description="Weight: 25%. Ratio of approved/issued source documents (0.0 to 1.0)")
    retrieval_sufficiency_score: float = Field(..., description="Weight: 25%. Sufficiency gate pass & top relevance (0.0 to 1.0)")
    coverage_score: float = Field(..., description="Weight: 15%. Proportion of required knowledge categories covered (0.0 to 1.0)")
    intent_confidence: float = Field(..., description="Weight: 10%. Intent classification certainty (0.0 to 1.0)")
    conflict_penalty: float = Field(default=0.0, description="Deduction for contradictory engineering data (e.g. 0.30)")
    obsolete_penalty: float = Field(default=0.0, description="Deduction for obsolete or superseded documents (e.g. 0.50)")
    raw_score: float = Field(..., description="Composite weighted score before clamp (0.0 to 1.0)")
    final_score: float = Field(..., description="Final clamped score (0.0 to 1.0)")
    formula: str = Field(
        default="0.25*Asset + 0.25*Source + 0.25*Sufficiency + 0.15*Coverage + 0.10*Intent - Penalties",
        description="Auditable mathematical formula"
    )


class QueryTraceLatency(BaseModel):
    """
    Latency and execution trace per pipeline stage.
    """
    query_id: str = Field(..., description="Unique query execution trace ID (e.g. Q-240927-1042)")
    timestamp: str = Field(..., description="ISO 8601 execution timestamp")
    nlu_latency_ms: float = Field(default=0.0, description="Query understanding & entity resolution time (ms)")
    retrieval_latency_ms: float = Field(default=0.0, description="Hybrid vector + lexical retrieval time (ms)")
    sufficiency_latency_ms: float = Field(default=0.0, description="Sufficiency gate & conflict check time (ms)")
    generation_latency_ms: float = Field(default=0.0, description="Answer synthesis & formatting time (ms)")
    total_latency_ms: float = Field(default=0.0, description="End-to-end processing latency (ms)")


class GeneratedAnswer(BaseModel):
    """
    Final factual answer contract independent of any LLM vendor or retrieval backend.
    """
    query: str
    equipment_tag: Optional[str] = None
    equipment_name: Optional[str] = None
    intent: str
    summary_answer: str = Field(..., description="Executive summary of the answer")
    detailed_points: List[str] = Field(default_factory=list, description="Claim-level or point-by-point details")
    confidence: ConfidenceLevel = Field(..., description="Categorical confidence level")
    confidence_reason: str = Field(..., description="Explicit rationale for confidence level")
    confidence_breakdown: Optional[ConfidenceBreakdown] = Field(None, description="Decomposed mathematical audit of confidence")
    query_id: Optional[str] = Field(None, description="Unique execution query ID")
    trace: Optional[QueryTraceLatency] = Field(None, description="Latency breakdown per stage")
    citations: List[SourceCitation] = Field(default_factory=list, description="Traceable citations to evidence items")
    recommendations: List[OperationalRecommendation] = Field(
        default_factory=list,
        description="Decoupled operational actions (empty for pure factual queries)"
    )
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None

    # Backward compatibility helper for existing tests
    @property
    def recommended_actions(self) -> List[OperationalRecommendation]:
        return self.recommendations

    @property
    def confidence_score(self) -> float:
        if self.confidence_breakdown is not None:
            return round(self.confidence_breakdown.final_score, 2)
        # Categorical fallback mapping for reporting
        mapping = {
            ConfidenceLevel.HIGH: 0.90,
            ConfidenceLevel.MEDIUM: 0.65,
            ConfidenceLevel.LOW: 0.35,
            ConfidenceLevel.UNVERIFIED: 0.10
        }
        return mapping.get(self.confidence, 0.50)

