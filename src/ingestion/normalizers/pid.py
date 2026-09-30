from typing import List, Dict, Any, Tuple
from pathlib import Path
import openpyxl

from schemas.common import DocumentSource, DocumentStatus, DocumentType
from schemas.document import DocumentChunk
from schemas.technical import TechnicalRecord
from schemas.relationship import RelationshipRecord
from src.ingestion.metadata import normalize_revision, normalize_status, normalize_unit, resolve_equipment


def normalize_pid_excel(
    file_path: Path
) -> Tuple[List[RelationshipRecord], List[TechnicalRecord], List[DocumentChunk]]:
    """
    Parses P&ID Register into:
    1. RelationshipRecord[] (hardened: monitors vs triggers_trip vs permissive_for vs controls)
    2. TechnicalRecord[] (instrument setpoints preserving instrument context)
    3. DocumentChunk[] (narrative register)
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

    raw_doc_id = meta.get("doc_no", "")
    tag_raw = meta.get("equipment_tag")
    res = resolve_equipment(tag_raw)
    tag = res["equipment_tag"] if res.get("status") == "resolved" else (tag_raw or "Asset")

    # Canonical document id
    doc_id = raw_doc_id if raw_doc_id and "XXXX" not in raw_doc_id else f"TJC-LLD-PID-{tag.replace('GA-', '')}"
    
    # Never infer revision if missing
    rev = normalize_revision(meta.get("revision"))
    status = normalize_status(meta.get("revision_status")) or DocumentStatus.ISSUED_FOR_OPERATION
    status_str = status.value if hasattr(status, "value") else str(status)
    source_file = meta.get("source_file") or file_path.name.replace(".xlsx", ".png")

    source = DocumentSource(
        file_name=source_file,
        page=1,
        sheet="Instrument List",
        revision=rev,
        status=status
    )

    relationships: List[RelationshipRecord] = []
    technical_records: List[TechnicalRecord] = []
    inst_lines: List[str] = []

    if "Instrument List" in wb.sheetnames:
        ws = wb["Instrument List"]
        for r in range(3, ws.max_row + 1):
            itag = ws.cell(r, 1).value
            desc = ws.cell(r, 2).value
            itype = ws.cell(r, 3).value
            sp = ws.cell(r, 4).value
            unit = ws.cell(r, 5).value
            fn = ws.cell(r, 6).value
            rel_il = ws.cell(r, 7).value
            loc = ws.cell(r, 8).value

            if not itag:
                continue

            itag_str = str(itag).strip()
            desc_str = str(desc).strip() if desc else itag_str
            itype_str = str(itype).strip() if itype else ""
            fn_str = str(fn).strip() if fn else ""
            sp_str = str(sp).strip() if sp and str(sp).strip() not in ("—", "-") else None
            unit_str = normalize_unit(str(unit).strip()) if unit and str(unit).strip() not in ("—", "-") else None

            # 1. TechnicalRecord for setpoint (Finding #2: Preserve instrument context!)
            if sp_str:
                tr = TechnicalRecord(
                    record_id=f"TR-{itag_str}-SETPOINT",
                    record_type="setpoint",
                    equipment_tag=tag,
                    document_id=doc_id,
                    document_type=DocumentType.PID,
                    category="Instrumentation Setpoint",
                    parameter=f"{itag_str} Setpoint",
                    canonical_field="instrument_setpoint",
                    source_label=f"{desc_str} Setpoint",
                    value=sp_str,
                    unit=unit_str,
                    source=source,
                    metadata={
                        "instrument_tag": itag_str,
                        "instrument_type": itype_str,
                        "instrument_description": desc_str,
                        "function": fn_str
                    }
                )
                technical_records.append(tr)

            # 2. RelationshipRecord (Audit Findings #3 & #4 FIX: Hardened semantics!)
            # Rule:
            # - ONLY trip switches / relays explicitly functioning as trip initiators get 'triggers_trip'
            # - Transmitters (PT, VT, TT, FIT) and indicators (PI, FI) get 'monitors'
            # - Permissive limit switches (ZSO, PDI) get 'permissive_for'
            # - Valves (XV, FV, RO) get 'controls'
            fn_lower = fn_str.lower()
            itype_lower = itype_str.lower()

            if "trip initiator" in fn_lower or ("switch" in itype_lower and "trip" in fn_lower) or ("relay" in itype_lower and "trip" in fn_lower):
                pred = "triggers_trip"
            elif "permissive" in fn_lower or "start permissive" in fn_lower:
                pred = "permissive_for"
            elif "valve" in itype_lower or "orifice" in itype_lower or "control" in fn_lower or "isolation" in fn_lower:
                pred = "controls"
            elif "transmitter" in itype_lower or "indicator" in itype_lower or "monitoring" in fn_lower or "measurement" in fn_lower:
                pred = "monitors"
            else:
                pred = "monitors"

            rel = RelationshipRecord(
                relationship_id=f"REL-PID-{itag_str}",
                source_tag=itag_str,
                relationship=pred,
                target_tag=tag,
                equipment_tag=tag,
                document_id=doc_id,
                document_type=DocumentType.PID,
                context=f"{desc_str} ({itype_str}). Function: {fn_str}. Location: {loc}",
                source=source,
                metadata={
                    "instrument_type": itype_str,
                    "related_interlock": str(rel_il) if rel_il and str(rel_il).strip() != "—" else None
                }
            )
            relationships.append(rel)

            sp_info = f" [Setpoint: {sp_str} {unit_str or ''}]" if sp_str else ""
            inst_lines.append(f"- {itag_str}: {desc_str} ({itype_str}){sp_info}. Function: {fn_str}. Location: {loc}")

    # 3. DocumentChunk narrative
    content_lines = [
        f"PIPING & INSTRUMENTATION DIAGRAM (P&ID) REGISTER: {tag} ({meta.get('equipment_name', 'Equipment')}).",
        f"Document No: {doc_id}, Revision: {rev or 'N/A'}, Status: {status_str}.",
        f"Area: {meta.get('area', '1200')}, Functional Location: {meta.get('functional_location', 'TJC-LLD-1200-01')}.",
        "INSTRUMENT & PROCESS CONTROL LOOPS:",
        "\n".join(inst_lines),
        f"CROSS REFERENCES: Datasheet: {meta.get('datasheet_reference', '')}, Interlock: {meta.get('interlock_reference', '')}."
    ]
    chunk = DocumentChunk(
        chunk_id=f"{doc_id}-P01-C01",
        document_id=doc_id,
        document_type=DocumentType.PID,
        title=f"Piping & Instrumentation Diagram Register - {tag}",
        equipment_tag=tag,
        content="\n".join(content_lines),
        source=source,
        metadata={"total_instruments": len(inst_lines)}
    )

    return relationships, technical_records, [chunk]
