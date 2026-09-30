import pytest
from schemas.common import DocumentSource, DocumentStatus, DocumentType
from schemas.technical import TechnicalRecord
from schemas.relationship import RelationshipRecord
from src.ingestion.validator import validate_knowledge_object, validate_batch


def test_validate_valid_technical_record():
    tr = TechnicalRecord(
        record_id="TR-TEST-001",
        record_type="technical_parameter",
        equipment_tag="GA-1201A",
        document_id="DS-TEST",
        document_type=DocumentType.DATASHEET,
        category="Design",
        parameter="Rated Flow",
        value=45,
        unit="m3/h",
        source=DocumentSource(file_name="test.pdf", page=1, revision="Rev.01", status=DocumentStatus.APPROVED)
    )
    is_valid, err, model = validate_knowledge_object(tr)
    assert is_valid is True
    assert err is None


def test_validate_invalid_object_missing_source():
    obj = {
        "record_id": "TR-INVALID",
        "equipment_tag": "GA-1201A",
        "document_id": "DS-TEST",
        "document_type": "DATASHEET",
        "category": "Design",
        "parameter": "Flow",
        "value": 10
        # source is missing
    }
    is_valid, err, model = validate_knowledge_object(obj)
    assert is_valid is False
    assert "source" in err.lower()


def test_validate_batch():
    batch = {
        "technical_records": [
            {
                "record_id": "TR-TEST-002",
                "equipment_tag": "GA-1201A",
                "document_id": "DS-TEST",
                "document_type": "DATASHEET",
                "category": "Design",
                "parameter": "Head",
                "value": 120,
                "unit": "m",
                "source": {
                    "file_name": "test.pdf",
                    "page": 1,
                    "revision": "Rev.01",
                    "status": "Approved"
                }
            }
        ]
    }
    res = validate_batch(batch)
    assert res["passed"] is True
    assert res["valid_objects"] == 1
    assert res["invalid_objects"] == 0
