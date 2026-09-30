import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import json
from collections import defaultdict
import datetime
from typing import List, Optional, Dict, Any

import pandas as pd
from schemas.maintenance import MaintenanceRecord


COLUMN_ALIASES = {
    "equipment_tag": ["equipment_tag", "equipment tag", "tag no", "tag_no", "tag", "equipment", "equipment id", "asset", "asset tag", "functional location"],
    "event_id": ["event_id", "work order", "work order no", "order", "notification", "id", "wo no", "wo_no", "event id", "no", "record id"],
    "date": ["date", "failure date", "incident date", "order date", "malfunction date", "start date", "notification date", "event date"],
    "failure_mode": ["failure_mode", "failure mode", "failure type", "breakdown mode", "defect", "mode", "failure mechanism", "problem type"],
    "symptom": ["symptom", "problem description", "problem", "description", "issue", "symptoms", "observed symptom", "breakdown description"],
    "root_cause": ["root_cause", "root cause", "cause", "underlying cause", "rca", "cause description", "reason"],
    "corrective_action": ["corrective_action", "action taken", "corrective action", "action", "work done", "resolution", "repair action", "activities"],
    "downtime_hours": ["downtime_hours", "downtime", "downtime (hours)", "downtime (hrs)", "duration (hrs)", "hours", "total downtime", "duration"],
    "parts_replaced": ["parts_replaced", "parts replaced", "spare parts", "parts", "components replaced", "material used", "spares"]
}


def _match_column(df_cols: List[str], alias_list: List[str]) -> Optional[str]:
    col_map = {str(c).strip().lower(): str(c) for c in df_cols}
    for alias in alias_list:
        if alias in col_map:
            return col_map[alias]
        # Partial containment check
        for raw_lower, orig in col_map.items():
            if alias in raw_lower or raw_lower in alias:
                return orig
    return None


def _find_header_and_load(file_path: Path, sheet_name: str) -> pd.DataFrame:
    # Read first 10 rows without header to locate where headers are
    raw_preview = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=10)
    target_header_row = 0

    for row_idx, row in raw_preview.iterrows():
        row_str = " ".join([str(val).lower() for val in row if pd.notna(val)])
        # Check if row looks like a header row
        keywords = ["tag", "equipment", "date", "problem", "cause", "failure", "action", "order"]
        matches = sum(1 for kw in keywords if kw in row_str)
        if matches >= 2:
            target_header_row = row_idx
            break

    df = pd.read_excel(file_path, sheet_name=sheet_name, header=target_header_row)
    return df


def parse_maintenance_excel(file_path: Path) -> List[MaintenanceRecord]:
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    xls = pd.ExcelFile(file_path)
    print(f"Sheets found in Excel: {xls.sheet_names}")
    all_records: List[MaintenanceRecord] = []

    for sheet_name in xls.sheet_names:
        df = _find_header_and_load(file_path, sheet_name)
        if df.empty:
            continue

        cols = [str(c).strip() for c in df.columns]
        print(f"\n[Sheet: '{sheet_name}'] Columns detected: {cols}")

        matched = {field: _match_column(cols, aliases) for field, aliases in COLUMN_ALIASES.items()}
        print(f"Matched columns mapping: {matched}")

        if not matched["equipment_tag"]:
            print(f"[WARN] Skipped sheet '{sheet_name}': Could not identify 'equipment_tag' column.")
            continue

        sheet_records = 0
        for idx, row in df.iterrows():
            tag_val = row[matched["equipment_tag"]]
            if pd.isna(tag_val):
                continue
            tag = str(tag_val).strip()
            if not tag or tag.lower() in ("nan", "none", ""):
                continue

            event_id = str(row[matched["event_id"]]).strip() if matched["event_id"] and pd.notna(row[matched["event_id"]]) else f"MNT-{tag}-{idx+1:03d}"

            # Parse date
            raw_date = row[matched["date"]] if matched["date"] and pd.notna(row[matched["date"]]) else None
            parsed_date: datetime.date = datetime.date.today()
            if isinstance(raw_date, (datetime.datetime, pd.Timestamp)):
                parsed_date = raw_date.date()
            elif isinstance(raw_date, datetime.date):
                parsed_date = raw_date
            elif isinstance(raw_date, str):
                try:
                    parsed_date = pd.to_datetime(raw_date).date()
                except Exception:
                    pass

            # Downtime
            raw_dt = row[matched["downtime_hours"]] if matched["downtime_hours"] and pd.notna(row[matched["downtime_hours"]]) else 0.0
            try:
                downtime = float(raw_dt) if pd.notna(raw_dt) else 0.0
            except (ValueError, TypeError):
                downtime = 0.0

            # Parts replaced
            raw_parts = str(row[matched["parts_replaced"]]) if matched["parts_replaced"] and pd.notna(row[matched["parts_replaced"]]) else ""
            parts = [p.strip() for p in raw_parts.split(",") if p.strip()] if raw_parts and raw_parts.lower() != "nan" else []

            record = MaintenanceRecord(
                event_id=event_id,
                equipment_tag=tag,
                date=parsed_date,
                failure_mode=str(row[matched["failure_mode"]]).strip() if matched["failure_mode"] and pd.notna(row[matched["failure_mode"]]) else "Unspecified",
                symptom=str(row[matched["symptom"]]).strip() if matched["symptom"] and pd.notna(row[matched["symptom"]]) else "Not documented",
                root_cause=str(row[matched["root_cause"]]).strip() if matched["root_cause"] and pd.notna(row[matched["root_cause"]]) else "Investigation pending",
                corrective_action=str(row[matched["corrective_action"]]).strip() if matched["corrective_action"] and pd.notna(row[matched["corrective_action"]]) else "Corrective action taken",
                downtime_hours=max(0.0, downtime),
                parts_replaced=parts
            )
            all_records.append(record)
            sheet_records += 1

        print(f"Loaded {sheet_records} records from sheet '{sheet_name}'.")

    return all_records


class MaintenanceRegistry:
    def __init__(self, records: List[MaintenanceRecord]):
        self._records = records
        self._by_tag = defaultdict(list)
        for r in records:
            self._by_tag[r.equipment_tag.upper()].append(r)

    def get_all(self) -> List[MaintenanceRecord]:
        return list(self._records)

    def get_by_tag(self, tag: str) -> List[MaintenanceRecord]:
        return list(self._by_tag.get(tag.upper(), []))

    def get_summary(self) -> Dict[str, Any]:
        tag_counts = {t: len(recs) for t, recs in self._by_tag.items()}
        total_dt = sum(r.downtime_hours for r in self._records)
        return {
            "total_records": len(self._records),
            "equipment_count": len(self._by_tag),
            "records_per_equipment": tag_counts,
            "total_downtime_hours": round(total_dt, 1)
        }


def run_maintenance_ingestion(
    excel_path: Optional[Path] = None,
    output_json: Optional[Path] = None
) -> MaintenanceRegistry:
    base_dir = Path(__file__).resolve().parent.parent.parent
    if excel_path is None:
        default_p1 = base_dir / "Case 1_ Manufacturing Knowledge Hub-20260919T101738Z-1-001" / "Case 1_ Manufacturing Knowledge Hub" / "Maintenance History (All Equipment).xlsx"
        default_p2 = base_dir / "data" / "raw" / "Maintenance History (All Equipment).xlsx"
        excel_path = default_p1 if default_p1.exists() else default_p2

    if output_json is None:
        output_json = base_dir / "data" / "extracted" / "maintenance_history.json"

    print(f"Loading maintenance records from: {excel_path}")
    records = parse_maintenance_excel(excel_path)
    registry = MaintenanceRegistry(records)

    # Export to JSON
    output_json.parent.mkdir(parents=True, exist_ok=True)
    serializable = [r.model_dump(mode="json") for r in records]
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)

    summary = registry.get_summary()
    print(f"\n[SUMMARY] Successfully ingested {summary['total_records']} events across {summary['equipment_count']} equipment units.")
    print(f"Total historical downtime: {summary['total_downtime_hours']} hrs")
    print(f"Output saved to: {output_json}")
    return registry


if __name__ == "__main__":
    run_maintenance_ingestion()
