import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
import openpyxl

from schemas.common import DocumentSource, DocumentStatus, DocumentType
from schemas.document import DocumentChunk
from schemas.relationship import RelationshipRecord
from src.ingestion.metadata import normalize_revision, normalize_status, resolve_equipment


def normalize_interlock_excel(
    file_path: Path
) -> Tuple[List[RelationshipRecord], List[DocumentChunk]]:
    """
    Parses Interlock Logic & Cause/Effect Matrix into:
    1. RelationshipRecord[] (triggers_trip, permissive_for)
       - Hardened: Only creates relationships for explicitly identified instrument/equipment tags.
       - Discards pseudo-entities like '—' or 'DCS reset'.
    2. DocumentChunk[] (narrative shutdown logic for RAG)
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    meta: Dict[str, str] = {}
    if "Metadata" in wb.sheetnames:
        ws = wb["Metadata"]
        for r in range(1, ws.max_row + 1):
            k = ws.cell(r, 1).value
            v = ws.cell(r, 2).value
            if k and v:
                meta[str(k).strip()] = str(v).strip()

    doc_id = meta.get("doc_no") or f"IL-{meta.get('equipment_tag', 'EQ')}"
    raw_tag = meta.get("equipment_tag")
    res = resolve_equipment(raw_tag)
    tag = res["equipment_tag"] if res.get("status") == "resolved" else (raw_tag or "Asset")

    # Never infer revision if missing
    rev = normalize_revision(meta.get("revision"))
    status = normalize_status(meta.get("revision_status")) or DocumentStatus.ISSUED_FOR_OPERATION
    status_str = status.value if hasattr(status, "value") else str(status)
    logic_no = meta.get("logic_no", "SEQ-LOGIC")
    sil_level = meta.get("sil_level", "SIL 1")
    source_file = meta.get("source_file") or file_path.name.replace(".xlsx", ".pdf")

    source = DocumentSource(
        file_name=source_file,
        page=1,
        sheet="Cause Effect",
        revision=rev,
        status=status
    )

    relationships: List[RelationshipRecord] = []
    trip_summary_lines: List[str] = []

    # 1. Parse Cause Effect Trips
    if "Cause Effect" in wb.sheetnames:
        ws = wb["Cause Effect"]
        # Dynamically discover effect columns from row 2
        effect_cols = {}
        for c in range(7, ws.max_column + 1):
            col_hdr = ws.cell(2, c).value
            if col_hdr and str(col_hdr).strip():
                raw_name = str(col_hdr).strip()
                eff_match = re.match(r"eff_?(\d+)[_ ]*(.*)", raw_name, re.IGNORECASE)
                if eff_match:
                    num = eff_match.group(1)
                    act_name = eff_match.group(2).replace("_", " ").title()
                    tag_in_col = None
                    if "xv" in raw_name.lower():
                        tag_in_col = "XV-" + tag.split("-")[-1].rstrip("AB")
                    elif "fv" in raw_name.lower():
                        tag_in_col = "FV-" + tag.split("-")[-1].rstrip("AB")
                    elif "standby" in raw_name.lower() or "spare" in raw_name.lower():
                        tag_in_col = (tag[:-1] + "B") if tag.endswith("A") else "STANDBY"
                    elif "dcs" in raw_name.lower() or "alarm" in raw_name.lower():
                        tag_in_col = "DCS"

                    if "trip" in raw_name.lower() and "motor" in raw_name.lower():
                        eff_label = f"Trip Motor (EFF-{num})"
                        target_cand = tag
                    elif "close" in raw_name.lower():
                        eff_label = f"Close Discharge {tag_in_col or ''} (EFF-{num})".replace("  ", " ").strip()
                        target_cand = tag_in_col or tag
                    elif "open" in raw_name.lower():
                        eff_label = f"Open Min-Flow {tag_in_col or ''} (EFF-{num})".replace("  ", " ").strip()
                        target_cand = tag_in_col or tag
                    elif "alarm" in raw_name.lower() or "annunciate" in raw_name.lower():
                        eff_label = f"DCS Alarm (EFF-{num})"
                        target_cand = "DCS"
                    elif "standby" in raw_name.lower() or "spare" in raw_name.lower():
                        eff_label = f"Start Standby Pump {tag_in_col or ''} (EFF-{num})".replace("  ", " ").strip()
                        target_cand = tag_in_col or tag
                    else:
                        eff_label = f"{act_name} (EFF-{num})"
                        target_cand = tag
                else:
                    eff_label = raw_name.replace("_", " ").title()
                    target_cand = tag
                effect_cols[c] = (eff_label, target_cand)

        for r in range(3, ws.max_row + 1):
            trip_id = ws.cell(r, 2).value
            desc = ws.cell(r, 3).value
            tag_inst = ws.cell(r, 4).value
            sp = ws.cell(r, 5).value
            voting = ws.cell(r, 6).value

            if trip_id and str(trip_id).strip().startswith("T") and len(str(trip_id).strip()) <= 4:
                effs = []
                targets = []
                for c, (eff_label, target_cand) in effect_cols.items():
                    val = str(ws.cell(r, c).value or "").strip().upper()
                    if val == "X":
                        effs.append(eff_label)
                        targets.append(target_cand)

                actions_str = ", ".join(effs)
                trip_summary_lines.append(f"- {trip_id}: {desc} ({tag_inst} {sp}, {voting}) -> Actions: {actions_str}")

                # Ensure source_tag is an actual tag
                clean_tag_inst = str(tag_inst).strip() if tag_inst else None
                if clean_tag_inst and clean_tag_inst not in ("—", "-", "None", ""):
                    ctx = f"{desc} (Setpoint: {sp}, Voting: {voting})"
                    rel = RelationshipRecord(
                        relationship_id=f"REL-{logic_no}-{trip_id}",
                        source_tag=clean_tag_inst,
                        relationship="triggers_trip",
                        target_tag=tag,
                        equipment_tag=tag,
                        document_id=doc_id,
                        document_type=DocumentType.INTERLOCK,
                        context=ctx,
                        source=source,
                        metadata={
                            "trip_id": str(trip_id),
                            "actions": effs,
                            "targets": targets,
                            "sil_level": sil_level
                        }
                    )
                    relationships.append(rel)

    # 2. Parse Start Permissives
    perm_summary_lines: List[str] = []
    if "Start Permissive" in wb.sheetnames:
        ws_p = wb["Start Permissive"]
        for r in range(3, ws_p.max_row + 1):
            p_id = ws_p.cell(r, 2).value
            p_desc = ws_p.cell(r, 3).value
            sig = ws_p.cell(r, 4).value
            gate = ws_p.cell(r, 5).value
            if p_id and p_desc:
                perm_summary_lines.append(f"- {p_id}: {p_desc} ({sig}, Gate: {gate})")
                clean_sig = str(sig).strip() if sig else ""
                
                # AUDIT FIX #3: Only create RelationshipRecord if sig is an actual instrument/valve tag!
                # Tags follow plant tagging convention like ZSO-1201, PDI-1201.
                # Skip conditions like 'DCS reset' or null placeholder '—'.
                is_valid_tag = bool(re.match(r"^[A-Z0-9]{2,5}-\d+", clean_sig))
                if is_valid_tag:
                    rel_p = RelationshipRecord(
                        relationship_id=f"REL-{logic_no}-{p_id}",
                        source_tag=clean_sig,
                        relationship="permissive_for",
                        target_tag=tag,
                        equipment_tag=tag,
                        document_id=doc_id,
                        document_type=DocumentType.INTERLOCK,
                        context=f"{p_desc} (Logic Gate: {gate})",
                        source=DocumentSource(
                            file_name=source_file,
                            page=1,
                            sheet="Start Permissive",
                            revision=rev,
                            status=status
                        ),
                        metadata={"permissive_id": str(p_id), "gate": str(gate)}
                    )
                    relationships.append(rel_p)

    default_pid = f"TJC-LLD-PID-{tag.replace('GA-', '')}"
    default_ds = f"TJC-LLD-DS-{tag}"
    content_lines = [
        f"INTERLOCK LOGIC & CAUSE EFFECT MATRIX: {logic_no} ({meta.get('logic_description', 'Shutdown Logic')}).",
        f"Document No: {doc_id}, Revision: {rev or 'N/A'}, Status: {status_str}, SIL Level: {sil_level}.",
        f"Equipment: {tag}, Functional Location: {meta.get('functional_location', 'TJC-LLD-1200-01')}.",
        "CAUSE & EFFECT MATRIX (TRIPS):",
        "\n".join(trip_summary_lines),
        "START PERMISSIVES (AND-gate conditions to start):",
        "\n".join(perm_summary_lines),
        f"CROSS REFERENCES: P&ID: {meta.get('pid_reference', default_pid)}, Datasheet: {meta.get('datasheet_reference', default_ds)}."
    ]
    content = "\n".join(content_lines)

    chunk = DocumentChunk(
        chunk_id=f"{doc_id}-P01-C01",
        document_id=doc_id,
        document_type=DocumentType.INTERLOCK,
        title=f"Interlock Logic & Cause Effect Matrix - {tag} ({logic_no})",
        equipment_tag=tag,
        content=content,
        source=source,
        metadata={
            "logic_no": logic_no,
            "sil_level": sil_level,
            "total_trips": len(trip_summary_lines),
            "total_permissives": len(perm_summary_lines)
        }
    )

    return relationships, [chunk]
