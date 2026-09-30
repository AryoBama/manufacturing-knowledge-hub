from datetime import date
from pathlib import Path
import pytest
from pydantic import ValidationError

from schemas.common import DocumentSource, DocumentStatus
from schemas.document import DocumentChunk
from schemas.maintenance import MaintenanceRecord
from src.ingestion.contract_validator import validate_file


def test_valid_document_chunk():
    source = DocumentSource(
        file_name="Equipment Datasheet - GA-1201A.pdf",
        page=1,
        revision="Rev 3",
        status=DocumentStatus.ISSUED_FOR_OPERATION
    )
    chunk = DocumentChunk(
        chunk_id="TJC-LLD-DS-GA-1201A-P01-C01",
        document_id="TJC-LLD-DS-GA-1201A",
        document_type="DATASHEET",
        title="Centrifugal Pump Data Sheet",
        equipment_tag="GA-1201A",
        content="Pump flow 45 m3/h at 120m head",
        source=source
    )
    assert chunk.chunk_id == "TJC-LLD-DS-GA-1201A-P01-C01"
    assert chunk.source.status == DocumentStatus.ISSUED_FOR_OPERATION


def test_chunk_id_violating_invariant_fails():
    source = DocumentSource(
        file_name="test.pdf",
        page=1,
        revision="Rev 1",
        status=DocumentStatus.APPROVED
    )
    with pytest.raises(ValidationError) as exc:
        DocumentChunk(
            chunk_id="random_id_123",  # DOES NOT start with document_id!
            document_id="TJC-LLD-DS-GA-1201A",
            document_type="DATASHEET",
            title="Pump Specs",
            content="Valid content length here",
            source=source
        )
    assert "violates ID rule" in str(exc.value)


def test_invalid_status_enum_fails():
    with pytest.raises(ValidationError):
        DocumentSource(
            file_name="test.pdf",
            page=1,
            revision="Rev 1",
            status="InvalidNonExistentStatus"  # not in enum
        )


def test_valid_maintenance_record_date():
    m = MaintenanceRecord(
        event_id="MNT-GA1201A-001",
        equipment_tag="GA-1201A",
        date="2025-08-14",  # string ISO parses into datetime.date
        failure_mode="Bearing Wear",
        symptom="Vibration",
        root_cause="Fatigue",
        corrective_action="Replaced bearing",
        downtime_hours=2.5
    )
    assert isinstance(m.date, date)
    assert m.date == date(2025, 8, 14)


def test_gold_standard_files_pass_validation():
    base_dir = Path(__file__).resolve().parent.parent

    # Datasheet
    ds_res = validate_file(base_dir / "data" / "extracted" / "Set_01_GA-1201A" / "datasheet.json")
    assert all(valid for _, valid, _ in ds_res)

    # Interlock
    il_res = validate_file(base_dir / "data" / "extracted" / "Set_01_GA-1201A" / "interlock.json")
    assert all(valid for _, valid, _ in il_res)

    # Maintenance
    mnt_res = validate_file(base_dir / "data" / "extracted" / "samples" / "maintenance_sample.json")
    assert all(valid for _, valid, _ in mnt_res)

    # Invalid sample fails
    inv_res = validate_file(base_dir / "data" / "extracted" / "samples" / "invalid_sample.json")
    assert any(not valid for _, valid, _ in inv_res)
