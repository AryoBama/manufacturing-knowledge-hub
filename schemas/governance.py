from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from schemas.common import DocumentStatus, DocumentSource


class ConflictType(str, Enum):
    NUMERIC_CONFLICT = "NUMERIC_CONFLICT"
    REVISION_CONFLICT = "REVISION_CONFLICT"
    STATUS_CONFLICT = "STATUS_CONFLICT"
    PROCEDURE_CONFLICT = "PROCEDURE_CONFLICT"
    ASSET_CONFLICT = "ASSET_CONFLICT"


class ConflictRecord(BaseModel):
    """
    Records an explicit contradiction detected between two or more authoritative sources.
    The system never guesses or forces an arbitrary resolution.
    """
    conflict_type: ConflictType = Field(..., description="Category of conflict detected")
    entity_tag: Optional[str] = Field(None, description="Equipment or instrument tag involved")
    parameter_name: str = Field(..., description="Parameter or field in dispute, e.g. PSLL trip setpoint")
    source_a: DocumentSource = Field(..., description="First source metadata")
    value_a: str = Field(..., description="Claim or value from Source A")
    source_b: DocumentSource = Field(..., description="Second source metadata")
    value_b: str = Field(..., description="Claim or value from Source B")
    resolution_status: str = Field(default="UNRESOLVED", description="UNRESOLVED | REVISION_RESOLVED | AUTHORITY_RESOLVED")
    recommended_action: str = Field(
        default="Verify against the latest approved operating source.",
        description="Guidance for engineering clarification"
    )


class DocumentLifecycleRecord(BaseModel):
    """
    Formal document lifecycle and provenance tracking.
    """
    document_id: str = Field(..., description="Unique document code")
    revision: str = Field(..., description="Revision label, e.g. Rev 3")
    status: DocumentStatus = Field(..., description="Formal lifecycle status")
    effective_date: Optional[str] = Field(None, description="ISO date when document became effective")
    approval_date: Optional[str] = Field(None, description="ISO date of engineering approval")
    expiry_date: Optional[str] = Field(None, description="ISO date when revision expires")
    document_owner: Optional[str] = Field(None, description="Engineering discipline or owner, e.g. Mechanical / Process")
    supersedes: Optional[str] = Field(None, description="Prior revision ID superseded by this document")
    superseded_by: Optional[str] = Field(None, description="Newer revision ID superseding this document")


class RevisionLineage(BaseModel):
    """
    Lineage tree connecting sequential revisions of a document.
    """
    document_family_id: str
    active_revision: str
    revisions: List[DocumentLifecycleRecord] = Field(default_factory=list)
