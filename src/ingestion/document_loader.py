import json
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Optional

from schemas.common import DocumentSource, DocumentStatus, DocumentType
from schemas.document import DocumentChunk


class DocumentRegistry:
    def __init__(self, chunks: List[DocumentChunk]):
        dedup_dict = {c.chunk_id: c for c in chunks}
        self._chunks = list(dedup_dict.values())
        self._by_tag = defaultdict(list)
        self._by_type = defaultdict(list)
        self._by_doc_id = defaultdict(list)
        self._by_chunk_id = {}

        for chunk in self._chunks:
            self._by_chunk_id[chunk.chunk_id] = chunk
            if chunk.equipment_tag:
                self._by_tag[chunk.equipment_tag.upper()].append(chunk)
            self._by_type[str(chunk.document_type).upper()].append(chunk)
            self._by_doc_id[chunk.document_id.upper()].append(chunk)

    def get_all(self) -> List[DocumentChunk]:
        return list(self._chunks)

    def get_by_chunk_id(self, chunk_id: str) -> Optional[DocumentChunk]:
        return self._by_chunk_id.get(chunk_id)

    def get_by_tag(self, tag: str) -> List[DocumentChunk]:
        return list(self._by_tag.get(tag.upper(), []))

    def get_by_type(self, doc_type: str) -> List[DocumentChunk]:
        return list(self._by_type.get(doc_type.upper(), []))

    def get_by_doc_id(self, doc_id: str) -> List[DocumentChunk]:
        return list(self._by_doc_id.get(doc_id.upper(), []))

    def __len__(self) -> int:
        return len(self._chunks)


def load_documents_from_dir(directory: Path) -> DocumentRegistry:
    chunks: List[DocumentChunk] = []
    if not directory.exists():
        return DocumentRegistry([])

    for json_file in sorted(directory.rglob("*.json")):
        if "invalid" in json_file.name or "report" in json_file.name:
            continue

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "maintenance" in json_file.name:
                m_items = data if isinstance(data, list) else [data]
                if m_items and isinstance(m_items[0], dict) and "event_id" in m_items[0]:
                    by_tag = defaultdict(list)
                    for ev in m_items:
                        t = ev.get("equipment_tag")
                        if not t:
                            cand = json_file.parent.name
                            if cand.lower() in ("json", "extracted", "processed"):
                                cand = json_file.parent.parent.name
                            t = cand if cand and "-" in cand else "UNKNOWN"
                        by_tag[t].append(ev)

                    for tag, ev_list in by_tag.items():
                        chunk_id = f"SAP-PM-HIST-{tag}-P01-C01"
                        if any(c.chunk_id == chunk_id for c in chunks):
                            continue
                        lines = [f"SAP PM MAINTENANCE WORK ORDER HISTORY & BREAKDOWN LOG - {tag}:"]
                        for ev in ev_list:
                            eid = ev.get("event_id")
                            dt_val = ev.get("date")
                            act = ev.get("corrective_action") or ev.get("symptom") or ""
                            rc = ev.get("root_cause") or ""
                            fm = ev.get("failure_mode") or "None (Routine Inspection/Proof Test)"
                            down = ev.get("downtime_hours", 0.0)
                            lines.append(f"- Event {eid} ({dt_val}): Failure Mode: {fm}, Downtime: {down}h. Cause: {rc}. Action: {act}")
                        chunk = DocumentChunk(
                            chunk_id=chunk_id,
                            document_id="SAP-PM-HIST",
                            document_type="MAINTENANCE",
                            title=f"SAP PM Maintenance History - {tag}",
                            equipment_tag=tag,
                            content="\n".join(lines),
                            source=DocumentSource(
                                file_name="Maintenance History.xlsx",
                                page=1,
                                revision=None,
                                status=DocumentStatus.APPROVED
                            )
                        )
                        chunks.append(chunk)
                continue

            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and "chunk_id" in item:
                    chunks.append(DocumentChunk.model_validate(item))
        except Exception as e:
            print(f"[WARN] Error loading {json_file}: {e}")

    return DocumentRegistry(chunks)
