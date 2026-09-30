from typing import Optional, Union, Any, Dict
from pydantic import Field

from schemas.common import CanonicalKnowledgeBase, DocumentSource, DocumentType


class TechnicalRecord(CanonicalKnowledgeBase):
    """
    STEP 2: TechnicalRecord
    For structured parameter/value/unit data (Datasheet, P&ID instrument specs, technical limits).
    Enables structured lookup (e.g. 'What is the rated flow of GA-1201A?' -> parameter='Rated Flow', value=45, unit='m3/h').
    Preserves both canonical_field AND exact source_label.
    """
    record_id: str = Field(
        ...,
        description="Unique technical record ID, e.g. TR-GA1201A-RATED-FLOW or DS-GA1201A-001"
    )
    record_type: str = Field(
        default="technical_parameter",
        description="Category: technical_parameter, design_limit, setpoint, coordinate, material"
    )
    category: str = Field(
        ...,
        description="Parameter group: Pump Design, Motor Data, Material, Electrical, Location"
    )
    parameter: str = Field(
        ...,
        description="Standard or cleaned parameter name, e.g. Rated Flow, Output Power"
    )
    value: Union[float, int, str, bool] = Field(
        ...,
        description="Extracted value (numerical float/int or string/boolean)"
    )
    unit: Optional[str] = Field(
        None,
        description="Standardized engineering unit, e.g. m3/h, bar, kW, rpm, m, degC"
    )
    canonical_field: Optional[str] = Field(
        None,
        description="Normalized key from semantic mapping, e.g. rated_flow, motor_power"
    )
    source_label: Optional[str] = Field(
        None,
        description="Original exact terminology/label in the raw document, e.g. Rated Capacity"
    )
