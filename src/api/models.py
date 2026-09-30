from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class QueryApiRequest(BaseModel):
    """Payload for technical Q&A query."""
    query: str = Field(..., description="Natural language technical question")
    equipment_tag: Optional[str] = Field(None, description="Explicit target equipment tag if known, e.g. GA-1201A")
    session_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session memory or engineering context")


class FailureMemorySearchRequest(BaseModel):
    """Payload for failure memory symptom search."""
    query: str = Field(..., description="Observed symptom, alarm, or problem statement")
    equipment_tag: Optional[str] = Field(None, description="Target equipment tag to isolate search")
    top_k: int = Field(default=5, ge=1, le=20, description="Max similar incidents to retrieve")


class PathSearchRequest(BaseModel):
    """Payload for knowledge graph causal path search."""
    source_tag: str = Field(..., description="Originating node tag, e.g. RO-1201")
    target_tag: str = Field(..., description="Destination node tag, e.g. MECH-SEAL-1201A")
    max_depth: int = Field(default=4, ge=1, le=8, description="Maximum BFS search depth")


class HealthResponse(BaseModel):
    """Liveness probe: basic process status."""
    status: str = "ok"
    service: str = "Chandra Asri Manufacturing Knowledge Hub API"
    version: str = "1.0.0"
    total_maintenance_records: int
    total_relationships: int
    active_equipment: List[str]


class ReadinessResponse(BaseModel):
    """Readiness probe: subsystem readiness check."""
    status: str = "ready"
    document_registry: str = "ready"
    vector_store: str = "ready"
    structured_store: str = "ready"
    failure_memory: str = "ready"
    plant_graph: str = "ready"
    total_documents: int
    total_maintenance_records: int
    total_relationships: int
    active_equipment: List[str]

