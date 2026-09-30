from enum import Enum
from typing import Optional, Union, Any, Dict, List
from pydantic import BaseModel, Field

from schemas.common import CanonicalKnowledgeBase, DocumentSource, DocumentType


class RelationshipType(str, Enum):
    # Plant hierarchy & topology
    LOCATED_IN = "LOCATED_IN"
    PART_OF = "PART_OF"
    CONNECTED_TO = "CONNECTED_TO"
    FEEDS_INTO = "feeds_into"
    
    # Instrumentation & Control
    MEASURES = "MEASURES"
    MONITORS = "monitors"
    CONTROLS = "controls"
    
    # Safety & Protection
    PROTECTED_BY = "PROTECTED_BY"
    TRIPPED_BY = "TRIPPED_BY"
    TRIGGERS_TRIP = "triggers_trip"
    PERMISSIVE_START = "PERMISSIVE_START"
    PERMISSIVE_FOR = "permissive_for"
    BYPASSES = "bypasses"
    
    # Failure & Operational Causality
    HAS_FAILURE_MODE = "HAS_FAILURE_MODE"
    HAS_HISTORY = "HAS_HISTORY"
    CAUSES = "CAUSES"
    DEPENDS_ON = "DEPENDS_ON"
    SUPERSEDES = "SUPERSEDES"

    def __str__(self) -> str:
        return self.value


class RelationshipRecord(CanonicalKnowledgeBase):
    """
    STEP 4: RelationshipRecord
    Captures topological, control, and safety relationships between plant entities (P&ID loops, Interlock Cause-Effect, Permissives).
    Essential for answering: 'What protects GA-1201A from high vibration?' -> VSHH-1201 triggers_trip GA-1201A.
    """
    relationship_id: str = Field(
        ...,
        description="Unique relationship ID, e.g. REL-SEQ1201-T3 or PID-PDI1201-PERM"
    )
    source_tag: str = Field(
        ...,
        description="Originating instrument, equipment, component, or system tag, e.g. VSHH-1201, PSLL-1201, ZSO-1201"
    )
    relationship: Union[RelationshipType, str] = Field(
        ...,
        description="Predicate: triggers_trip, permissive_for, monitors, controls, LOCATED_IN, PART_OF, etc."
    )
    target_tag: str = Field(
        ...,
        description="Target equipment, plant area, failure mode, or actuator tag, e.g. GA-1201A, XV-1201, FV-1201"
    )
    context: Optional[str] = Field(
        None,
        description="Operational context, voting logic, or setpoint limit, e.g. Bearing vibration > 7.1 mm/s RMS (1oo2)"
    )


class PlantHierarchyNode(BaseModel):
    """Represents an entity node in the plant topological/safety graph."""
    tag: str = Field(..., description="Entity tag or identifier, e.g. GA-1201A or AREA-12")
    level: str = Field(..., description="Hierarchy level: PLANT, AREA, UNIT, EQUIPMENT, COMPONENT, INSTRUMENT, PROTECTION, FAILURE_MODE, ACTION")
    description: Optional[str] = Field(None, description="Human readable description")
    parent_tag: Optional[str] = Field(None, description="Immediate hierarchical parent tag")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom node properties")


class GraphPath(BaseModel):
    """A directed path between two entities in the knowledge graph."""
    hops: List[str] = Field(..., description="Sequence of node tags from start to end")
    relationships: List[str] = Field(..., description="Predicates along the path")
    contexts: List[Optional[str]] = Field(default_factory=list, description="Context annotations for each edge")
    total_hops: int = Field(..., description="Number of edges traversed")


class GraphTraversalResult(BaseModel):
    """Result of multi-hop graph querying or hierarchy traversal."""
    source_node: str = Field(..., description="Starting node tag")
    target_node: Optional[str] = Field(None, description="Target node tag if pathfinding")
    paths: List[GraphPath] = Field(default_factory=list, description="Found directed paths")
    related_nodes: List[str] = Field(default_factory=list, description="All discovered related nodes within traversal scope")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Query execution details")

