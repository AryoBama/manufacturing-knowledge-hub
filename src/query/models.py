from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ResolutionSource(str, Enum):
    EXPLICIT_QUERY = "explicit_query"
    CONVERSATION_CONTEXT = "conversation_context"
    UI_CONTEXT = "ui_context"
    INFERRED = "inferred"
    NONE = "none"


class ResolutionConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class KnowledgeType(str, Enum):
    OPERATING_PROCEDURE = "operating_procedure"
    PROCESS_LOGIC = "process_logic"
    PROTECTION_LOGIC = "protection_logic"
    FAILURE_HISTORY = "failure_history"
    EQUIPMENT_SPEC = "equipment_spec"
    PHYSICAL_LOCATION = "physical_location"
    GENERAL_KNOWLEDGE = "general_knowledge"


class QueryRequest(BaseModel):
    query: str = Field(..., description="Raw technical question from the engineer")
    equipment_tag: Optional[str] = Field(None, description="Explicit equipment tag if provided by caller")
    session_context: Dict[str, Any] = Field(default_factory=dict, description="Context from chat history or UI state")


class ResolutionMetadata(BaseModel):
    source: ResolutionSource = Field(..., description="Origin where equipment was resolved")
    confidence: ResolutionConfidence = Field(
        ...,
        description="Confidence level in determining the target asset (NOT the answer confidence)"
    )
    candidate_tags: List[str] = Field(
        default_factory=list,
        description="Candidate equipment tags when ambiguous or multiple matches are detected"
    )


class QueryUnderstanding(BaseModel):
    query: str
    intent: str = Field(
        ...,
        description="equipment_information | procedure | troubleshooting | failure_history | protection | location | general_information"
    )
    equipment_tag: Optional[str] = None
    resolution: ResolutionMetadata
    entities: Dict[str, Any] = Field(default_factory=dict)
    knowledge_types: List[str] = Field(
        default_factory=list,
        description="Types of information required (e.g. operating_procedure, protection_logic), NOT document types"
    )
    requires_clarification: bool = False
    clarification_reason: Optional[str] = None
