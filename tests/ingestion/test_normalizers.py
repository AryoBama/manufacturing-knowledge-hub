import pytest
from pathlib import Path
from schemas.common import DocumentSource, DocumentStatus, DocumentType
from src.ingestion.normalizers import (
    normalize_datasheet_excel,
    normalize_opl_excel,
    normalize_maintenance_excel,
    normalize_interlock_excel,
    normalize_pid_excel,
    normalize_plot_plan_excel
)

SOURCE_DIR = Path(__file__).resolve().parent.parent.parent / "GA-1201A HEXANE FEED PUMP"


def test_datasheet_normalizer():
    ds_file = SOURCE_DIR / "Equipment Datasheet - GA-1201A.xlsx"
    trs, chunks = normalize_datasheet_excel(ds_file)
    assert len(trs) >= 15
    assert len(chunks) == 1
    # Check rated flow value
    flow_tr = next((t for t in trs if t.canonical_field == "rated_flow"), None)
    assert flow_tr is not None
    assert flow_tr.value == 45
    assert flow_tr.unit == "m3/h"


def test_opl_normalizer():
    opl_file = SOURCE_DIR / "OPL GA-1201A-HEXANE_FEED_PUMP.xlsx"
    chunks = normalize_opl_excel(opl_file)
    assert len(chunks) == 7
    for c in chunks:
        assert c.document_type == DocumentType.OPL
        assert len(c.content) > 100


def test_maintenance_normalizer():
    mnt_file = SOURCE_DIR / "Maintenance History GA-1201A.xlsx"
    recs = normalize_maintenance_excel(mnt_file)
    assert len(recs) == 26
    for r in recs:
        assert r.equipment_tag == "GA-1201A"
        assert r.downtime_hours >= 0.0


def test_interlock_normalizer():
    il_file = SOURCE_DIR / "Interlock GA-1201A.xlsx"
    rels, chunks = normalize_interlock_excel(il_file)
    assert len(rels) >= 6
    assert any(r.relationship == "triggers_trip" for r in rels)
    assert any(r.relationship == "permissive_for" for r in rels)


def test_pid_normalizer():
    pid_file = SOURCE_DIR / "PID Register GA-1201A.xlsx"
    rels, trs, chunks = normalize_pid_excel(pid_file)
    assert len(rels) >= 15
    assert len(trs) >= 3
    assert len(chunks) == 1


def test_audit_p0_relationship_semantic_purity():
    """Verify transmitters do not trigger trips, and pseudo-entities are filtered."""
    pid_file = SOURCE_DIR / "PID Register GA-1201A.xlsx"
    il_file = SOURCE_DIR / "Interlock GA-1201A.xlsx"
    pid_rels, _, _ = normalize_pid_excel(pid_file)
    il_rels, _ = normalize_interlock_excel(il_file)
    all_rels = pid_rels + il_rels

    # PT-1201 & VT-1201 must monitor, NEVER trigger trips
    pt_rel = next((r for r in all_rels if r.source_tag == "PT-1201"), None)
    assert pt_rel is not None
    assert pt_rel.relationship == "monitors"

    vt_rel = next((r for r in all_rels if r.source_tag == "VT-1201"), None)
    assert vt_rel is not None
    assert vt_rel.relationship == "monitors"

    # No pseudo-entities
    invalid_tags = {"DCS reset", "—", "-", "", "None"}
    for r in all_rels:
        assert r.source_tag not in invalid_tags
        assert r.target_tag not in invalid_tags


def test_audit_p0_maintenance_semantics():
    """Verify failure_occurred is boolean and failure_mode contains NO Yes/No strings."""
    mnt_file = SOURCE_DIR / "Maintenance History GA-1201A.xlsx"
    recs = normalize_maintenance_excel(mnt_file)
    
    for r in recs:
        assert isinstance(r.failure_occurred, bool)
        if not r.failure_occurred:
            assert r.failure_mode is None
        else:
            assert r.failure_mode is not None
            assert r.failure_mode.lower() not in ("yes", "no", "true", "false")


def test_audit_p1_technical_records_and_status():
    """Verify unmapped parameters preserve source_label and status doesn't leak Python repr."""
    ds_file = SOURCE_DIR / "Equipment Datasheet - GA-1201A.xlsx"
    trs, _ = normalize_datasheet_excel(ds_file)

    # Check unmapped parameters
    unmapped = [t for t in trs if t.canonical_field is None]
    assert len(unmapped) > 0
    for u in unmapped:
        assert u.source_label is not None
        assert len(u.source_label) > 0

    # Check status string representation
    for t in trs:
        assert "DocumentStatus." not in str(t.source.status)
