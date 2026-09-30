from datetime import date
from pathlib import Path

from schemas.common import DocumentSource, DocumentStatus
from schemas.document import DocumentChunk
from schemas.maintenance import MaintenanceRecord
from src.ingestion.document_loader import DocumentRegistry, load_documents_from_dir
from src.ingestion.maintenance_loader import MaintenanceRegistry


def test_document_registry():
    src = DocumentSource(
        file_name="GA-1201A.pdf",
        page=1,
        revision="Rev 3",
        status=DocumentStatus.ISSUED_FOR_OPERATION
    )
    chunk = DocumentChunk(
        chunk_id="TJC-LLD-DS-GA-1201A-P01-C01",
        document_id="TJC-LLD-DS-GA-1201A",
        document_type="DATASHEET",
        title="Pump Data Sheet",
        equipment_tag="GA-1201A",
        content="Centrifugal pump specifications...",
        source=src
    )
    reg = DocumentRegistry([chunk])
    assert len(reg) == 1
    assert len(reg.get_by_tag("GA-1201A")) == 1
    assert len(reg.get_by_tag("NON_EXISTENT")) == 0
    assert len(reg.get_by_type("DATASHEET")) == 1
    assert reg.get_by_chunk_id("TJC-LLD-DS-GA-1201A-P01-C01") is not None


def test_load_documents_from_extracted_dir():
    base_dir = Path(__file__).resolve().parent.parent
    extracted_dir = base_dir / "data" / "extracted"

    registry = load_documents_from_dir(extracted_dir)
    assert len(registry) >= 2  # At least datasheet and interlock
    ga_docs = registry.get_by_tag("GA-1201A")
    assert len(ga_docs) >= 2


def test_maintenance_registry():
    rec1 = MaintenanceRecord(
        event_id="MNT-01",
        equipment_tag="GA-1201A",
        date=date(2025, 1, 15),
        failure_mode="Vibration",
        symptom="High noise",
        root_cause="Bearing failure",
        corrective_action="Replaced bearing",
        downtime_hours=3.5
    )
    rec2 = MaintenanceRecord(
        event_id="MNT-02",
        equipment_tag="GA-1201A",
        date=date(2025, 4, 10),
        failure_mode="Leakage",
        symptom="Drip at seal",
        root_cause="Seal face worn",
        corrective_action="Replaced mechanical seal",
        downtime_hours=2.0
    )
    reg = MaintenanceRegistry([rec1, rec2])
    assert len(reg.get_all()) == 2
    assert len(reg.get_by_tag("GA-1201A")) == 2

    summary = reg.get_summary()
    assert summary["total_records"] == 2
    assert summary["equipment_count"] == 1
    assert summary["total_downtime_hours"] == 5.5
