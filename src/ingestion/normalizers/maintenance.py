import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from schemas.common import DocumentSource, DocumentStatus, DocumentType
from schemas.maintenance import MaintenanceRecord
from src.ingestion.metadata import resolve_equipment


COLUMN_ALIASES = {
    "equipment_tag": ["equipment_tag", "equipment tag", "tag no", "tag_no", "tag", "equipment", "asset"],
    "event_id": ["event_id", "wo_number", "work order", "notification_no", "notification", "id"],
    "date": ["date", "report_date", "failure date", "incident date", "order date", "start_date"],
    "breakdown": ["breakdown", "failure_mode", "failure type", "defect", "mode"],
    "symptom": ["symptom", "problem_description", "problem", "description", "issue"],
    "root_cause": ["root_cause", "cause", "underlying cause", "rca", "reason"],
    "corrective_action": ["corrective_action", "action taken", "corrective action", "action", "work done"],
    "downtime_hours": ["downtime_hours", "downtime", "downtime (hours)", "duration (hrs)", "hours"],
    "parts_replaced": ["parts_replaced", "spare_parts_used", "spare parts", "parts", "spares"]
}


def _match_column(df_cols: List[str], alias_list: List[str]) -> Optional[str]:
    col_map = {str(c).strip().lower(): str(c) for c in df_cols}
    for alias in alias_list:
        if alias in col_map:
            return col_map[alias]
        for raw_lower, orig in col_map.items():
            if alias in raw_lower or raw_lower in alias:
                return orig
    return None


def _deduce_failure_mode(raw_breakdown: str, symptom_text: str, root_cause_text: str) -> Optional[str]:
    """
    Deduces a meaningful failure mode string only when an actual failure occurred.
    Returns None if routine maintenance without breakdown.
    """
    combined = f"{symptom_text} {root_cause_text}".lower()
    if "vibration" in combined and "misalignment" in combined:
        return "Shaft / Coupling Misalignment"
    elif "vibration" in combined:
        return "High Vibration / Resonance"
    elif "seal" in combined and "leak" in combined:
        return "Mechanical Seal Degradation / Leak"
    elif "bearing" in combined or "spalling" in combined:
        return "Bearing Fatigue / Spalling"
    elif "grout" in combined or "crack" in combined:
        return "Baseplate / Foundation Degradation"
    elif "coupling" in combined:
        return "Coupling Element Fatigue"
    elif "overload" in combined:
        return "Motor Electrical / Overload Trip"
    elif "drift" in combined:
        return "Instrument Setpoint Drift"
    elif "plug" in combined or "fouled" in combined:
        return "Impulse Line / Orifice Fouling"
    else:
        return "Mechanical / Operational Failure"


def normalize_maintenance_records(
    df: pd.DataFrame,
    source_metadata: DocumentSource
) -> List[MaintenanceRecord]:
    """
    Normalizes a maintenance DataFrame into canonical MaintenanceRecords.
    Audit Finding #9: Strictly separates failure_occurred (bool) from failure_mode (str | None).
    Never stores 'Yes' or 'No' inside failure_mode.
    """
    cols = [str(c).strip() for c in df.columns]
    matched = {field: _match_column(cols, aliases) for field, aliases in COLUMN_ALIASES.items()}

    records: List[MaintenanceRecord] = []
    if not matched["equipment_tag"]:
        return records

    for idx, row in df.iterrows():
        raw_tag = row[matched["equipment_tag"]]
        if pd.isna(raw_tag):
            continue
        tag_str = str(raw_tag).strip()
        if not tag_str or tag_str.lower() in ("nan", "none", ""):
            continue

        res = resolve_equipment(tag_str)
        canon_tag = res["equipment_tag"] if res.get("status") == "resolved" else tag_str

        # Event ID
        event_id = None
        if matched["event_id"] and pd.notna(row[matched["event_id"]]):
            event_id = str(row[matched["event_id"]]).strip()
        if not event_id:
            event_id = f"MNT-{canon_tag}-{idx+1:03d}"

        # Date
        parsed_date: datetime.date = datetime.date.today()
        if matched["date"] and pd.notna(row[matched["date"]]):
            raw_d = row[matched["date"]]
            if isinstance(raw_d, (datetime.datetime, pd.Timestamp)):
                parsed_date = raw_d.date()
            elif isinstance(raw_d, datetime.date):
                parsed_date = raw_d
            else:
                try:
                    parsed_date = pd.to_datetime(str(raw_d)).date()
                except Exception:
                    pass

        # Downtime
        dt = 0.0
        if matched["downtime_hours"] and pd.notna(row[matched["downtime_hours"]]):
            try:
                dt = float(row[matched["downtime_hours"]])
            except (ValueError, TypeError):
                dt = 0.0

        # Parts Replaced
        parts: List[str] = []
        if matched["parts_replaced"] and pd.notna(row[matched["parts_replaced"]]):
            raw_parts = str(row[matched["parts_replaced"]]).strip()
            if raw_parts and raw_parts.lower() not in ("nan", "none", "-"):
                parts = [p.strip() for p in raw_parts.split(",") if p.strip()]

        symptom = str(row[matched["symptom"]]).strip() if matched["symptom"] and pd.notna(row[matched["symptom"]]) else None
        root_cause = str(row[matched["root_cause"]]).strip() if matched["root_cause"] and pd.notna(row[matched["root_cause"]]) else None
        corrective_action = str(row[matched["corrective_action"]]).strip() if matched["corrective_action"] and pd.notna(row[matched["corrective_action"]]) else None

        # AUDIT FIX #9: Parse failure_occurred vs failure_mode cleanly
        raw_bd = str(row[matched["breakdown"]]).strip() if matched["breakdown"] and pd.notna(row[matched["breakdown"]]) else ""
        is_failure = raw_bd.lower() in ("yes", "y", "true", "1") or dt > 0.0

        failure_mode = None
        if is_failure:
            # If raw breakdown value is an actual category string (not 'Yes'), use it
            if raw_bd.lower() not in ("yes", "y", "true", "1", "no", "n", "false", "0", ""):
                failure_mode = raw_bd
            else:
                failure_mode = _deduce_failure_mode(raw_bd, symptom or "", root_cause or "")
        else:
            failure_mode = None

        rec = MaintenanceRecord(
            event_id=event_id,
            equipment_tag=canon_tag,
            document_id="SAP-PM-HIST",
            document_type=DocumentType.MAINTENANCE,
            date=parsed_date,
            failure_occurred=is_failure,
            failure_mode=failure_mode,
            symptom=symptom,
            root_cause=root_cause,
            corrective_action=corrective_action,
            downtime_hours=max(0.0, dt),
            parts_replaced=parts,
            source=source_metadata,
            metadata={
                "row_index": int(idx),
                "original_tag": tag_str,
                "breakdown_flag": raw_bd or ("Yes" if is_failure else "No")
            }
        )
        records.append(rec)

    return records


def normalize_maintenance_excel(file_path: Path) -> List[MaintenanceRecord]:
    xls = pd.ExcelFile(file_path)
    all_recs: List[MaintenanceRecord] = []

    for sheet_name in xls.sheet_names:
        if sheet_name.lower() in ("explanation", "glossary", "readme"):
            continue

        raw_preview = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=10)
        target_header_row = 0
        for r_idx, r_val in raw_preview.iterrows():
            row_str = " ".join([str(v).lower() for v in r_val if pd.notna(v)])
            if sum(1 for kw in ["tag", "equipment", "date", "problem", "cause", "action", "order"] if kw in row_str) >= 2:
                target_header_row = r_idx
                break

        df = pd.read_excel(file_path, sheet_name=sheet_name, header=target_header_row)
        
        # AUDIT FIX #5: Do NOT default revision to 'Rev.00'; use None if not in workbook
        source = DocumentSource(
            file_name=file_path.name,
            page=1,
            sheet=sheet_name,
            revision=None,
            status=DocumentStatus.APPROVED
        )
        recs = normalize_maintenance_records(df, source)
        all_recs.extend(recs)

    return all_recs
