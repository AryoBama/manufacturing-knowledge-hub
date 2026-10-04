import pytest
from pathlib import Path
from schemas.common import DocumentType
from src.ingestion.adapter import adapt_file, detect_document_type_from_file

RAW_GA = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "GA-1201A"
LEGACY_GA = Path(__file__).resolve().parent.parent.parent / "GA-1201A HEXANE FEED PUMP"
SOURCE_DIR = RAW_GA if RAW_GA.exists() else LEGACY_GA


def test_detect_document_type():
    ds_file = SOURCE_DIR / "Equipment Datasheet - GA-1201A.xlsx"
    doc_type, warn = detect_document_type_from_file(ds_file)
    assert doc_type == DocumentType.DATASHEET
    assert warn is None

    il_file = SOURCE_DIR / "Interlock GA-1201A.xlsx"
    doc_type, warn = detect_document_type_from_file(il_file)
    assert doc_type == DocumentType.INTERLOCK

    opl_file = SOURCE_DIR / "OPL GA-1201A-HEXANE_FEED_PUMP.xlsx"
    doc_type, warn = detect_document_type_from_file(opl_file)
    assert doc_type == DocumentType.OPL


def test_adapt_datasheet_produces_technical_records():
    ds_file = SOURCE_DIR / "Equipment Datasheet - GA-1201A.xlsx"
    batch = adapt_file(ds_file)
    assert len(batch.technical_records) > 0
    assert len(batch.document_chunks) == 1
    # Verify no equipment hardcoding in adapter
    assert any(tr.canonical_field == "rated_flow" for tr in batch.technical_records)


def test_adapt_interlock_produces_relationships():
    il_file = SOURCE_DIR / "Interlock GA-1201A.xlsx"
    batch = adapt_file(il_file)
    assert len(batch.relationships) > 0
    assert any(r.relationship == "triggers_trip" for r in batch.relationships)
