import datetime
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field, model_validator

from schemas.common import CanonicalKnowledgeBase, DocumentSource, DocumentStatus, DocumentType



class MaintenanceRecord(CanonicalKnowledgeBase):
    """
    STEP 3: MaintenanceRecord
    For CMMS / SAP PM maintenance logs, failure events, symptoms, root cause, corrective actions.
    Separates failure_occurred (bool) from failure_mode (str | None).
    Inherits Common Metadata (equipment_tag, document_id, document_type, source).
    """
    @model_validator(mode="before")
    @classmethod
    def clean_failure_semantics(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_fm = str(data.get("failure_mode") or "").strip()
            dt = 0.0
            try:
                dt = float(data.get("downtime_hours") or 0.0)
            except (ValueError, TypeError):
                dt = 0.0

            if "failure_occurred" not in data or data.get("failure_occurred") is None:
                if raw_fm.lower() in ("yes", "true", "1", "y") or dt > 0.0:
                    data["failure_occurred"] = True
                elif raw_fm.lower() in ("no", "false", "0", "n", "none", "-", ""):
                    data["failure_occurred"] = False
                elif raw_fm:
                    data["failure_occurred"] = True
                else:
                    data["failure_occurred"] = False

            if not data.get("failure_occurred"):
                data["failure_mode"] = None
            else:
                if raw_fm.lower() in ("yes", "true", "1", "y", "no", "false", "none", "", "-"):
                    data["failure_mode"] = data.get("symptom") or data.get("root_cause") or "Unscheduled Failure"
        return data
    event_id: str = Field(
        ...,
        description="Unique maintenance event or work order ID, e.g. WO-240012 or NT-2024-560049"
    )
    equipment_tag: str = Field(
        ...,
        description="Target plant equipment tag, e.g. GA-1201A"
    )
    document_id: str = Field(
        default="SAP-PM-HIST",
        description="Originating document ID / log register ID"
    )
    document_type: Union[DocumentType, str] = Field(
        default=DocumentType.MAINTENANCE,
        description="Category: MAINTENANCE"
    )
    date: datetime.date = Field(
        ...,
        description="Event report date in ISO YYYY-MM-DD"
    )
    failure_occurred: bool = Field(
        default=False,
        description="True if actual unscheduled breakdown/failure occurred; False for routine preventive tasks, proof tests, inspections"
    )
    failure_mode: Optional[str] = Field(
        None,
        description="Specific failure mode (e.g. Mechanical seal leak, Bearing spalling); null for routine/non-failure tasks"
    )
    symptom: Optional[str] = Field(
        None,
        description="Observed anomaly, alarm, or problem description"
    )
    root_cause: Optional[str] = Field(
        None,
        description="Identified root cause or diagnosis (null if not a failure or routine inspection)"
    )
    corrective_action: Optional[str] = Field(
        None,
        description="Maintenance action taken to resolve the issue"
    )
    downtime_hours: float = Field(
        default=0.0,
        ge=0.0,
        description="Equipment downtime duration in hours"
    )
    parts_replaced: List[str] = Field(
        default_factory=list,
        description="List of replacement components or materials used"
    )
    source: DocumentSource = Field(
        default_factory=lambda: DocumentSource(
            file_name="Maintenance History (All Equipment).xlsx",
            page=1,
            sheet=None,
            revision=None,
            status=DocumentStatus.APPROVED
        ),
        description="Full source tracking metadata"
    )


class FailureModeFrequency(BaseModel):
    """Frequency and occurrence rate of specific failure modes."""
    failure_mode: str = Field(..., description="Failure mode name or category")
    count: int = Field(..., description="Number of historical occurrences")
    percentage: float = Field(..., description="Percentage of total failure occurrences (0.0 to 100.0)")
    sample_event_ids: List[str] = Field(default_factory=list, description="List of work order or notification event IDs")


class FailurePatternSummary(BaseModel):
    """High-level statistical failure pattern summary for an equipment tag."""
    equipment_tag: str = Field(..., description="Equipment tag, e.g. GA-1201A")
    total_maintenance_records: int = Field(..., description="Total work orders / notifications analyzed")
    failure_count: int = Field(..., description="Total breakdown or unscheduled failure events")
    non_failure_count: int = Field(..., description="Total routine preventive or proof test tasks")
    top_failure_modes: List[FailureModeFrequency] = Field(default_factory=list, description="Top ranked failure modes by occurrence")
    total_downtime_hours: float = Field(default=0.0, description="Cumulative downtime in hours from failures")
    earliest_record_date: Optional[str] = Field(None, description="Earliest recorded event date")
    latest_record_date: Optional[str] = Field(None, description="Most recent recorded event date")


class SimilarFailureCase(BaseModel):
    """A historical incident retrieved based on symptom or context similarity."""
    event_id: str = Field(..., description="Unique event ID, e.g. NT-2024-560011")
    equipment_tag: str = Field(..., description="Target equipment tag")
    date: str = Field(..., description="Incident date (ISO)")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Symptom/context similarity score")
    symptom: Optional[str] = Field(None, description="Reported symptom or observed anomaly")
    failure_mode: Optional[str] = Field(None, description="Classified failure mode")
    root_cause: Optional[str] = Field(None, description="Determined root cause")
    corrective_action: Optional[str] = Field(None, description="Maintenance action performed")
    parts_replaced: List[str] = Field(default_factory=list, description="Replacement parts used")
    source_file: str = Field(..., description="Source file name")
    document_id: str = Field(default="SAP-PM-HIST", description="CMMS / document ID")


class HistoricalRCAInsight(BaseModel):
    """Consolidated RCA and proven corrective action insights."""
    equipment_tag: str = Field(..., description="Equipment tag")
    root_causes: List[str] = Field(default_factory=list, description="Unique root causes identified in history")
    proven_actions: List[str] = Field(default_factory=list, description="Proven successful maintenance actions")
    replacement_parts_used: List[str] = Field(default_factory=list, description="Components historically replaced")
    reference_work_orders: List[str] = Field(default_factory=list, description="Associated work orders")


class FailureMemoryReport(BaseModel):
    """
    Active Failure Memory query output.
    Enforces the invariant: Historical evidence != Current diagnosis.
    """
    equipment_tag: str = Field(..., description="Target equipment tag")
    query_symptom: Optional[str] = Field(None, description="Input symptom query or anomaly description")
    has_historical_precedent: bool = Field(default=False, description="True if matching historical incidents were found")
    pattern_summary: Optional[FailurePatternSummary] = Field(None, description="Statistical pattern of failures")
    similar_cases: List[SimilarFailureCase] = Field(default_factory=list, description="Ranked past similar incidents")
    rca_insights: Optional[HistoricalRCAInsight] = Field(None, description="Verified historical root causes and solutions")
    disclaimer: str = Field(
        default="Historical evidence != Current diagnosis: Historical failure records indicate past occurrences, common root causes, and proven mitigations. They do not constitute an active real-time diagnosis for current plant conditions.",
        description="Mandatory engineering safety disclaimer"
    )

