from typing import Dict, Any, List, Tuple, Union, Optional
from pydantic import ValidationError

from schemas.common import CanonicalKnowledgeBase, DocumentStatus, DocumentType
from schemas.document import DocumentChunk
from schemas.technical import TechnicalRecord
from schemas.maintenance import MaintenanceRecord
from schemas.relationship import RelationshipRecord


def validate_knowledge_object(
    obj: Union[DocumentChunk, TechnicalRecord, MaintenanceRecord, RelationshipRecord, Dict[str, Any]]
) -> Tuple[bool, Optional[str], Optional[CanonicalKnowledgeBase]]:
    """
    Step 13: Validation.
    Validates any knowledge object against the 4 canonical schemas.
    Returns (is_valid, error_message, parsed_model).
    """
    if isinstance(obj, (DocumentChunk, TechnicalRecord, MaintenanceRecord, RelationshipRecord)):
        # Already parsed model, verify integrity invariants
        try:
            # Verify source presence
            if not obj.source or not obj.source.file_name:
                return False, "Missing source.file_name", None
            if not obj.document_id:
                return False, "Missing document_id", None
            return True, None, obj
        except Exception as e:
            return False, str(e), None

    if not isinstance(obj, dict):
        return False, f"Expected dictionary or Pydantic model, got {type(obj)}", None

    # Infer model type from attributes
    try:
        if "record_id" in obj:
            model = TechnicalRecord.model_validate(obj)
            return True, None, model
        elif "relationship_id" in obj:
            model = RelationshipRecord.model_validate(obj)
            return True, None, model
        elif "event_id" in obj:
            model = MaintenanceRecord.model_validate(obj)
            return True, None, model
        elif "chunk_id" in obj:
            model = DocumentChunk.model_validate(obj)
            return True, None, model
        else:
            return False, "Dictionary does not match any of the 4 canonical object signatures", None
    except ValidationError as e:
        error_details = [f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in e.errors()]
        return False, "; ".join(error_details), None
    except Exception as e:
        return False, str(e), None


def validate_batch(
    batch_dict: Dict[str, List[Any]]
) -> Dict[str, Any]:
    """
    Validates all lists in a batch and produces detailed validation metrics.
    """
    total_objects = 0
    valid_objects = 0
    invalid_objects = 0
    errors: List[str] = []

    for category, items in batch_dict.items():
        if category == "warnings":
            continue
        for idx, item in enumerate(items):
            total_objects += 1
            is_valid, err, _ = validate_knowledge_object(item)
            if is_valid:
                valid_objects += 1
            else:
                invalid_objects += 1
                errors.append(f"[{category}][{idx}]: {err}")

    return {
        "total_objects": total_objects,
        "valid_objects": valid_objects,
        "invalid_objects": invalid_objects,
        "errors": errors,
        "passed": invalid_objects == 0
    }
