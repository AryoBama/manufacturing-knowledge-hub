from enum import Enum
from typing import Optional, Union, Any, Dict
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    DATASHEET = "DATASHEET"
    PID = "PID"
    OPL = "OPL"
    INTERLOCK = "INTERLOCK"
    GA_DRAWING = "GA_DRAWING"
    PLOT_PLAN = "PLOT_PLAN"
    SOP = "SOP"
    MAINTENANCE = "MAINTENANCE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class DocumentStatus(str, Enum):
    APPROVED = "Approved"
    ISSUED_FOR_OPERATION = "Issued for Operation"
    ISSUED_FOR_REVIEW = "Issued for Review"
    ISSUED_FOR_CONSTRUCTION = "Issued for Construction"
    UNDER_REVIEW = "Under Review"
    SUPERSEDED = "Superseded"
    DRAFT = "Draft"
    OBSOLETE = "Obsolete"
    UNKNOWN = "Unknown"


    def __str__(self) -> str:
        return self.value


class DocumentSource(BaseModel):
    file_name: str = Field(..., description="Original file name, e.g. Equipment Datasheet - GA-1201A.pdf")
    page: int = Field(default=1, description="Physical page number of the evidence")
    sheet: Optional[str] = Field(None, description="Sheet name if sourced from workbook")
    revision: Optional[str] = Field(None, description="Document revision string, e.g. Rev 3, Rev.03 (null if unknown)")
    status: Optional[DocumentStatus] = Field(None, description="Formal release/approval status (null if unknown)")


class CanonicalKnowledgeBase(BaseModel):
    """
    Step 5: Common Metadata Base Model.
    All 4 Canonical Knowledge Objects inherit these mandatory traceability fields.
    """
    equipment_tag: Optional[str] = Field(None, description="Associated plant equipment tag, e.g. GA-1201A")
    document_id: str = Field(..., description="Official engineering document ID or reference number")
    document_type: Union[DocumentType, str] = Field(..., description="Canonical document category")
    source: DocumentSource = Field(..., description="Full source tracking and evidence metadata")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or raw extraction attributes")

    @property
    def revision(self) -> Optional[str]:
        return self.source.revision

    @property
    def status(self) -> Optional[str]:
        if self.source.status is not None:
            return self.source.status.value if hasattr(self.source.status, "value") else str(self.source.status)
        return None
