import pytest
from pathlib import Path
from schemas.document import DocumentChunk
from schemas.maintenance import MaintenanceRecord
from src.ingestion.convert_teammate_xlsx import (
    convert_datasheet,
    convert_interlock,
    convert_pid,
    convert_plot_plan,
    convert_opl,
    convert_all
)

RAW_GA = Path(__file__).resolve().parent.parent / "data" / "raw" / "GA-1201A"
LEGACY_GA = Path(__file__).resolve().parent.parent / "GA-1201A HEXANE FEED PUMP"
INPUT_DIR = RAW_GA if RAW_GA.exists() else LEGACY_GA


def test_convert_datasheet():
    ds_path = INPUT_DIR / "Equipment Datasheet - GA-1201A.xlsx"
    chunk = convert_datasheet(ds_path)
    assert isinstance(chunk, DocumentChunk)
    assert chunk.document_id == "TJC-LLD-DS-GA-1201A"
    assert chunk.equipment_tag == "GA-1201A"
    assert "45 m³/h" in chunk.content or "45" in chunk.content
    assert chunk.chunk_id.startswith(chunk.document_id)


def test_convert_interlock():
    il_path = INPUT_DIR / "Interlock GA-1201A.xlsx"
    chunk = convert_interlock(il_path)
    assert isinstance(chunk, DocumentChunk)
    assert chunk.document_id == "TJC-LLD-IL-GA-1201A"
    assert "PSLL-1201" in chunk.content
    assert "VSHH-1201" in chunk.content


def test_convert_pid():
    pid_path = INPUT_DIR / "PID Register GA-1201A.xlsx"
    chunk = convert_pid(pid_path)
    assert isinstance(chunk, DocumentChunk)
    assert chunk.document_id == "TJC-LLD-PID-1201"
    assert "PSLL-1201" in chunk.content
    assert "RO-1201" in chunk.content


def test_convert_plot_plan():
    pp_path = INPUT_DIR / "Plot Plan GA-1201A.xlsx"
    chunk = convert_plot_plan(pp_path)
    assert isinstance(chunk, DocumentChunk)
    assert chunk.document_id == "TJC-LLD-PP-GA-1201A"
    assert "A-3" in chunk.content
    assert "+0.00" in chunk.content


def test_convert_opl():
    opl_path = INPUT_DIR / "OPL GA-1201A-HEXANE_FEED_PUMP.xlsx"
    chunks = convert_opl(opl_path)
    assert len(chunks) == 7
    for c in chunks:
        assert isinstance(c, DocumentChunk)
        assert c.chunk_id.startswith(c.document_id)
        assert len(c.content) > 100
