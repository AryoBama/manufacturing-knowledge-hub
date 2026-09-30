import pytest
from pathlib import Path
from src.ingestion.pipeline import run_ingestion_pipeline

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_run_ingestion_pipeline(tmp_path):
    input_dir = BASE_DIR / "GA-1201A HEXANE FEED PUMP"
    output_dir = tmp_path / "processed"

    result = run_ingestion_pipeline(
        input_dir=input_dir,
        output_base_dir=output_dir,
        target_equipment_tag="GA-1201A"
    )

    assert result["equipment"] == "GA-1201A"
    assert result["quality_report"]["validation_passed"] is True
    assert result["quality_report"]["total_objects"] > 50

    dest_dir = result["dest_dir"]
    assert (dest_dir / "document_chunks.json").exists()
    assert (dest_dir / "technical_records.json").exists()
    assert (dest_dir / "maintenance_records.json").exists()
    assert (dest_dir / "relationships.json").exists()
    assert (dest_dir / "ingestion_report.json").exists()
