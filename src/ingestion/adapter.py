import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import openpyxl

from schemas.common import DocumentType, DocumentSource
from schemas.document import DocumentChunk
from schemas.technical import TechnicalRecord
from schemas.maintenance import MaintenanceRecord
from schemas.relationship import RelationshipRecord
from src.ingestion.metadata import normalize_document_type, normalize_revision, normalize_status
from src.ingestion.normalizers import (
    normalize_datasheet_excel,
    normalize_datasheet_data,
    normalize_opl_excel,
    normalize_maintenance_excel,
    normalize_interlock_excel,
    normalize_pid_excel,
    normalize_plot_plan_excel,
    normalize_generic_document
)


class IngestionBatch:
    """
    Container holding normalized canonical knowledge objects produced during ingestion.
    """
    def __init__(self):
        self.document_chunks: List[DocumentChunk] = []
        self.technical_records: List[TechnicalRecord] = []
        self.maintenance_records: List[MaintenanceRecord] = []
        self.relationships: List[RelationshipRecord] = []
        self.warnings: List[str] = []

    def extend(self, other: "IngestionBatch"):
        self.document_chunks.extend(other.document_chunks)
        self.technical_records.extend(other.technical_records)
        self.maintenance_records.extend(other.maintenance_records)
        self.relationships.extend(other.relationships)
        self.warnings.extend(other.warnings)

    @property
    def total_objects(self) -> int:
        return (
            len(self.document_chunks)
            + len(self.technical_records)
            + len(self.maintenance_records)
            + len(self.relationships)
        )


def detect_document_type_from_file(file_path: Path) -> Tuple[DocumentType, Optional[str]]:
    """
    Infers DocumentType from file name or Excel metadata sheets.
    """
    name_lower = file_path.name.lower()
    
    # Check filename patterns
    if "datasheet" in name_lower or "-ds-" in name_lower:
        return DocumentType.DATASHEET, None
    if "opl" in name_lower:
        return DocumentType.OPL, None
    if "maintenance" in name_lower or "history" in name_lower or "wo" in name_lower:
        return DocumentType.MAINTENANCE, None
    if "interlock" in name_lower or "-il-" in name_lower or "cause" in name_lower:
        return DocumentType.INTERLOCK, None
    if "pid" in name_lower or "p&id" in name_lower:
        return DocumentType.PID, None
    if "plot" in name_lower or "layout" in name_lower or "-pp-" in name_lower:
        return DocumentType.PLOT_PLAN, None

    # If it's an Excel file, check Metadata sheet for document_type
    if file_path.suffix.lower() == ".xlsx":
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
            if "Metadata" in wb.sheetnames:
                ws = wb["Metadata"]
                for r in range(1, min(15, ws.max_row + 1)):
                    k = str(ws.cell(r, 1).value or "").lower()
                    v = ws.cell(r, 2).value
                    if "document_type" in k and v:
                        return normalize_document_type(v)
            # Check sheet names
            snames = [s.lower() for s in wb.sheetnames]
            if any("cause" in s for s in snames):
                return DocumentType.INTERLOCK, None
            if any("instrument" in s for s in snames):
                return DocumentType.PID, None
            if any("location" in s for s in snames):
                return DocumentType.PLOT_PLAN, None
            if any("opl" in s or "mechanical seal" in s for s in snames):
                return DocumentType.OPL, None
        except Exception:
            pass

    return DocumentType.UNKNOWN, f"Could not determine document type for file '{file_path.name}'"


def adapt_file(file_path: Path) -> IngestionBatch:
    """
    STEP 9: Ingestion Adapter.
    Takes an extracted file (.xlsx or .json), determines its document type,
    and routes to the appropriate normalizer.
    CRITICAL: Logic NEVER checks equipment tag; branching is 100% based on document_type.
    """
    batch = IngestionBatch()
    if not file_path.exists():
        batch.warnings.append(f"File not found: {file_path}")
        return batch

    doc_type, warn = detect_document_type_from_file(file_path)
    if warn:
        batch.warnings.append(warn)

    suffix = file_path.suffix.lower()

    # Route by document_type
    try:
        if suffix == ".xlsx":
            if doc_type == DocumentType.DATASHEET:
                trs, chunks = normalize_datasheet_excel(file_path)
                batch.technical_records.extend(trs)
                batch.document_chunks.extend(chunks)

            elif doc_type == DocumentType.OPL:
                chunks = normalize_opl_excel(file_path)
                batch.document_chunks.extend(chunks)

            elif doc_type == DocumentType.MAINTENANCE:
                recs = normalize_maintenance_excel(file_path)
                batch.maintenance_records.extend(recs)

            elif doc_type == DocumentType.INTERLOCK:
                rels, chunks = normalize_interlock_excel(file_path)
                batch.relationships.extend(rels)
                batch.document_chunks.extend(chunks)

            elif doc_type == DocumentType.PID:
                rels, trs, chunks = normalize_pid_excel(file_path)
                batch.relationships.extend(rels)
                batch.technical_records.extend(trs)
                batch.document_chunks.extend(chunks)

            elif doc_type == DocumentType.PLOT_PLAN:
                trs, chunks = normalize_plot_plan_excel(file_path)
                batch.technical_records.extend(trs)
                batch.document_chunks.extend(chunks)

            else:
                batch.warnings.append(f"No specific normalizer for doc_type '{doc_type}' on Excel file: {file_path.name}")

        elif suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue

                # Check if item already has explicit document_type
                item_doc_type, _ = normalize_document_type(item.get("document_type", doc_type))

                if "parameters" in item and item_doc_type == DocumentType.DATASHEET:
                    src_dict = item.get("source", {})
                    src = DocumentSource(
                        file_name=src_dict.get("file_name", file_path.name),
                        page=int(src_dict.get("page", 1)),
                        revision=normalize_revision(src_dict.get("revision")),
                        status=normalize_status(src_dict.get("status"))
                    )
                    trs, chunks = normalize_datasheet_data(item, src)
                    batch.technical_records.extend(trs)
                    batch.document_chunks.extend(chunks)

                elif "event_id" in item or item_doc_type == DocumentType.MAINTENANCE:
                    # Maintenance item
                    try:
                        rec = MaintenanceRecord.model_validate(item)
                        batch.maintenance_records.append(rec)
                    except Exception as e:
                        batch.warnings.append(f"Failed validating maintenance JSON item: {e}")

                elif "relationship_id" in item:
                    try:
                        rel = RelationshipRecord.model_validate(item)
                        batch.relationships.append(rel)
                    except Exception as e:
                        batch.warnings.append(f"Failed validating relationship JSON item: {e}")

                elif "record_id" in item:
                    try:
                        tr = TechnicalRecord.model_validate(item)
                        batch.technical_records.append(tr)
                    except Exception as e:
                        batch.warnings.append(f"Failed validating technical record JSON item: {e}")

                elif "chunk_id" in item or "content" in item:
                    try:
                        chunk = DocumentChunk.model_validate(item)
                        batch.document_chunks.append(chunk)
                    except Exception as e:
                        # Fallback
                        chunks = normalize_generic_document(item)
                        batch.document_chunks.extend(chunks)
                else:
                    chunks = normalize_generic_document(item)
                    batch.document_chunks.extend(chunks)

    except Exception as e:
        batch.warnings.append(f"Error adapting {file_path.name}: {e}")

    return batch
