from typing import Dict, Any, Tuple, Union
from pydantic import ValidationError

from schemas.document import DocumentChunk
from schemas.maintenance import MaintenanceRecord


def validate_schema_dict(data: Dict[str, Any]) -> Tuple[bool, Union[DocumentChunk, MaintenanceRecord, str]]:
    """
    Validates a dictionary against DocumentChunk or MaintenanceRecord.
    Returns (True, parsed_model) if valid, or (False, error_message) if invalid.
    """
    try:
        if "event_id" in data:
            model = MaintenanceRecord.model_validate(data)
        else:
            model = DocumentChunk.model_validate(data)
        return True, model
    except ValidationError as e:
        error_details = [f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in e.errors()]
        return False, "; ".join(error_details)
    except Exception as e:
        return False, str(e)
