from typing import List, Dict, Any, Tuple
from pathlib import Path
import openpyxl

from schemas.common import DocumentSource, DocumentStatus, DocumentType
from schemas.document import DocumentChunk
from schemas.technical import TechnicalRecord
from src.ingestion.metadata import (
    find_canonical_field,
    normalize_revision,
    normalize_status,
    normalize_unit,
    resolve_equipment
)


def normalize_datasheet_data(
    raw_data: Dict[str, Any],
    source_metadata: DocumentSource
) -> Tuple[List[TechnicalRecord], List[DocumentChunk]]:
    """
    Normalizes Datasheet payload into TechnicalRecords and a summary DocumentChunk.
    raw_data can come from JSON payload or parsed Excel workbook.
    """
    equipment_tag = raw_data.get("equipment_tag")
    if equipment_tag:
        res = resolve_equipment(equipment_tag)
        if res.get("status") == "resolved":
            equipment_tag = res["equipment_tag"]

    doc_id = raw_data.get("document_id") or raw_data.get("doc_no") or f"DS-{equipment_tag or 'EQ'}"
    eq_name = raw_data.get("equipment_name", "Equipment")
    eq_type = raw_data.get("equipment_type")
    floc = raw_data.get("functional_location")
    service = raw_data.get("service")

    technical_records: List[TechnicalRecord] = []
    text_summary_lines: List[str] = [
        f"EQUIPMENT DATASHEET: {equipment_tag} ({eq_name}).",
        f"Document ID: {doc_id}, Revision: {source_metadata.revision}, Status: {source_metadata.status}.",
        f"Equipment Type: {eq_type or 'N/A'}.",
        f"Functional Location: {floc or 'N/A'}.",
        f"Service: {service or 'N/A'}."
    ]

    # Process parameters list or category dictionary
    params = raw_data.get("parameters", [])
    if isinstance(params, list):
        for idx, item in enumerate(params):
            cat = item.get("category", "General Specifications")
            param = item.get("parameter")
            val = item.get("value")
            unit_raw = item.get("unit")
            if not param or val is None or str(val).strip() in ("", "-", "—"):
                continue

            unit = normalize_unit(unit_raw)
            canon_field, std_unit = find_canonical_field(param)
            if std_unit and not unit:
                unit = std_unit

            # Parse numeric value if possible
            parsed_val: Any = val
            if isinstance(val, (int, float)):
                parsed_val = val
            else:
                try:
                    cleaned_val_str = str(val).replace(",", "").strip()
                    if "." in cleaned_val_str:
                        parsed_val = float(cleaned_val_str)
                    else:
                        parsed_val = int(cleaned_val_str)
                except (ValueError, TypeError):
                    parsed_val = str(val).strip()

            rec_id = f"TR-{doc_id}-{idx+1:03d}"
            tr = TechnicalRecord(
                record_id=rec_id,
                record_type="technical_parameter",
                equipment_tag=equipment_tag,
                document_id=doc_id,
                document_type=DocumentType.DATASHEET,
                category=cat,
                parameter=param,
                canonical_field=canon_field,
                source_label=param,
                value=parsed_val,
                unit=unit,
                source=source_metadata,
                metadata={
                    "equipment_type": eq_type,
                    "functional_location": floc
                }
            )
            technical_records.append(tr)
            unit_str = f" {unit}" if unit else ""
            text_summary_lines.append(f"{cat} - {param}: {val}{unit_str}")

    # Build summary DocumentChunk for RAG text retrieval
    content = "\n".join(text_summary_lines)
    chunk = DocumentChunk(
        chunk_id=f"{doc_id}-P01-C01",
        document_id=doc_id,
        document_type=DocumentType.DATASHEET,
        title=f"Equipment Datasheet - {eq_name} ({equipment_tag or 'Asset'})",
        equipment_tag=equipment_tag,
        equipment_type=eq_type,
        content=content,
        source=source_metadata,
        metadata={"total_parameters": len(technical_records)}
    )

    return technical_records, [chunk]


def normalize_datasheet_excel(
    file_path: Path
) -> Tuple[List[TechnicalRecord], List[DocumentChunk]]:
    """
    Reads an Equipment Datasheet .xlsx file and parses it into normalized objects.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    meta: Dict[str, Any] = {}
    if "Metadata" in wb.sheetnames:
        ws = wb["Metadata"]
        for r in range(1, ws.max_row + 1):
            k = ws.cell(r, 1).value
            v = ws.cell(r, 2).value
            if k and v:
                meta[str(k).strip()] = str(v).strip()

    doc_id = meta.get("doc_no") or f"DS-{meta.get('equipment_tag', 'EQ')}"
    eq_tag = meta.get("equipment_tag")
    rev = normalize_revision(meta.get("revision"))
    status = normalize_status(meta.get("revision_status"))
    source_file = meta.get("source_file") or file_path.name.replace(".xlsx", ".pdf")

    source = DocumentSource(
        file_name=source_file,
        page=1,
        revision=rev,
        status=status
    )

    parameters = []
    # Inspect all data sheets (e.g. Mechanical Data, Motor Data, Electrical)
    for sname in wb.sheetnames:
        if sname == "Metadata":
            continue
        ws = wb[sname]
        for r in range(2, ws.max_row + 1):
            cat = ws.cell(r, 1).value
            param = ws.cell(r, 2).value
            val = ws.cell(r, 3).value
            unit = ws.cell(r, 4).value
            if param and val and str(param).lower() != "parameter":
                parameters.append({
                    "category": str(cat).strip() if cat else sname,
                    "parameter": str(param).strip(),
                    "value": val,
                    "unit": str(unit).strip() if unit else None
                })

    payload = {
        "document_id": doc_id,
        "equipment_tag": eq_tag,
        "equipment_name": meta.get("equipment_name", "Equipment"),
        "equipment_type": meta.get("equipment_type"),
        "functional_location": meta.get("functional_location"),
        "service": meta.get("service"),
        "parameters": parameters
    }

    return normalize_datasheet_data(payload, source)
