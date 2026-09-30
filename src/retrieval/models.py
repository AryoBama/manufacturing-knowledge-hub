from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from schemas.common import DocumentSource
from schemas.governance import ConflictRecord
from src.query.models import QueryUnderstanding


class SufficiencyStatus(str, Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    CLARIFICATION_REQUIRED = "clarification_required"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    OUT_OF_SCOPE = "out_of_scope"


class RetrievalResult(BaseModel):
    chunk_id: str
    document_id: str
    document_type: str
    equipment_tag: Optional[str] = None
    content: str
    relevance_score: float = Field(default=0.0, description="Normalized score 0.0 - 1.0")
    source: DocumentSource


class SufficiencyCheck(BaseModel):
    status: SufficiencyStatus = Field(..., description="sufficient | insufficient | clarification_required | conflicting_evidence")
    reason: str = Field(..., description="Explanation of sufficiency evaluation")
    covered_knowledge_types: List[str] = Field(
        default_factory=list,
        description="Knowledge categories satisfied by current evidence"
    )
    uncovered_knowledge_types: List[str] = Field(
        default_factory=list,
        description="Knowledge categories still missing"
    )
    conflicts: List[ConflictRecord] = Field(
        default_factory=list,
        description="Contradictions detected between authoritative sources"
    )



class RetrievalResponse(BaseModel):
    query: str
    understanding: QueryUnderstanding
    results: List[RetrievalResult]
    sufficiency: SufficiencyCheck
