import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from schemas.common import DocumentSource, DocumentStatus
from schemas.governance import ConflictRecord
from src.query.models import QueryUnderstanding
from src.retrieval.models import RetrievalResult, SufficiencyCheck, SufficiencyStatus
from src.retrieval.structured_store import StructuredKnowledgeStore


class EvidenceItem(BaseModel):
    """
    Standardized, atomic evidence element across all knowledge modalities.
    Decouples generation from retrieval algorithms and storage backends.
    """
    evidence_id: str = Field(..., description="Stable, unique evidence identifier (e.g. EV-DOC-..., EV-TR-...)")
    content: str = Field(..., description="Verbatim textual or tabular representation of the evidence")
    equipment_tag: Optional[str] = Field(None, description="Associated plant equipment tag")
    document_id: str = Field(..., description="Official document identifier")
    document_type: str = Field(..., description="Canonical document type (DATASHEET, PID, INTERLOCK, OPL, MAINTENANCE)")
    source: DocumentSource = Field(..., description="Document source tracking with uninvented metadata")
    relevance_score: float = Field(default=0.0, description="Normalized relevance score 0.0 - 1.0")
    evidence_type: str = Field(
        ...,
        description="Modal type: 'document_chunk' | 'technical_parameter' | 'relationship' | 'maintenance_event'"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw extraction or contextual parameters")


class EvidencePackage(BaseModel):
    """
    Stable intermediate contract passed to the generation layer.
    Contains all fused evidence items along with sufficiency decisions.
    """
    query: str
    equipment_tag: Optional[str] = None
    intent: str
    items: List[EvidenceItem] = Field(default_factory=list)
    sufficiency: SufficiencyStatus
    sufficiency_reason: str
    covered_knowledge_types: List[str] = Field(default_factory=list)
    uncovered_knowledge_types: List[str] = Field(default_factory=list)
    conflicts: List[ConflictRecord] = Field(default_factory=list, description="Contradictions detected between authoritative sources")

    @property
    def is_sufficient(self) -> bool:
        return self.sufficiency == SufficiencyStatus.SUFFICIENT

    def get_items_by_type(self, evidence_type: str) -> List[EvidenceItem]:
        return [it for it in self.items if it.evidence_type == evidence_type]


class EvidenceFusionEngine:
    """
    Fuses multi-modal evidence (structured technical records, relationship matrices,
    maintenance history, and unstructured text chunks) into a unified EvidencePackage.
    """
    @staticmethod
    def fuse(
        understanding: QueryUnderstanding,
        retrieval_results: List[RetrievalResult],
        sufficiency: SufficiencyCheck,
        structured_store: Optional[StructuredKnowledgeStore] = None
    ) -> EvidencePackage:
        items: List[EvidenceItem] = []
        seen_ids = set()

        tag = understanding.equipment_tag

        # 1. Fuse Document Chunks from Retrieval Results
        for r in retrieval_results:
            ev_id = f"EV-DOC-{r.chunk_id}"
            if ev_id in seen_ids:
                continue
            seen_ids.add(ev_id)

            items.append(
                EvidenceItem(
                    evidence_id=ev_id,
                    content=r.content,
                    equipment_tag=r.equipment_tag,
                    document_id=r.document_id,
                    document_type=r.document_type,
                    source=r.source,
                    relevance_score=r.relevance_score,
                    evidence_type="document_chunk",
                    metadata={"chunk_id": r.chunk_id}
                )
            )

        # 2. Fuse Structured Records from StructuredKnowledgeStore if available
        if structured_store and tag:
            intent = understanding.intent

            # A. Technical Records (Parameters)
            if intent in ("equipment_information", "troubleshooting", "general_information"):
                keywords = ["flow", "head", "power", "speed", "pressure", "material", "temperature", "temp", "type"]
                stop_words = {"what", "how", "about", "the", "for", "and", "does", "can", "tell", "show", "is", "are", "with", "this", "that"}
                q_words = [
                    w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', understanding.query)
                    if w.lower() not in stop_words
                ]
                all_kws = list(dict.fromkeys(q_words + keywords))
                for kw in all_kws:
                    trs = structured_store.lookup_technical_parameter(tag, kw)
                    for tr in trs:
                        ev_id = f"EV-TR-{tr.record_id}"
                        if ev_id in seen_ids:
                            continue
                        seen_ids.add(ev_id)
                        content_str = f"{tr.parameter}: {tr.value} {tr.unit or ''}".strip()
                        items.append(
                            EvidenceItem(
                                evidence_id=ev_id,
                                content=content_str,
                                equipment_tag=tr.equipment_tag,
                                document_id=tr.document_id,
                                document_type=str(tr.document_type),
                                source=tr.source,
                                relevance_score=0.90,
                                evidence_type="technical_parameter",
                                metadata={"parameter": tr.parameter, "value": tr.value, "unit": tr.unit}
                            )
                        )

            # B. Relationship Records (Protection & Interlocks)
            if intent in ("protection", "troubleshooting"):
                rels = structured_store.lookup_relationships(tag)
                for rel in rels:
                    ev_id = f"EV-REL-{rel.relationship_id}"
                    if ev_id in seen_ids:
                        continue
                    seen_ids.add(ev_id)
                    content_str = f"Relationship [{rel.relationship}]: {rel.source_tag} -> {rel.target_tag} ({rel.context or ''})"
                    items.append(
                        EvidenceItem(
                            evidence_id=ev_id,
                            content=content_str,
                            equipment_tag=rel.equipment_tag or tag,
                            document_id=rel.document_id,
                            document_type=str(rel.document_type),
                            source=rel.source,
                            relevance_score=0.95,
                            evidence_type="relationship",
                            metadata={"relationship": rel.relationship, "source_tag": rel.source_tag, "target_tag": rel.target_tag}
                        )
                    )

            # C. Maintenance Records (Failure History & Troubleshooting)
            if intent in ("failure_history", "troubleshooting"):
                symptom = understanding.entities.get("symptom")
                mr_list = structured_store.lookup_maintenance(tag, symptom_keyword=symptom)
                for mr in mr_list[:10]:
                    ev_id = f"EV-MNT-{mr.event_id}"
                    if ev_id in seen_ids:
                        continue
                    seen_ids.add(ev_id)
                    fm_str = f"Failure: {mr.failure_mode}" if mr.failure_mode else "Routine/No Breakdown"
                    content_str = f"Work Order {mr.event_id} ({mr.date}): {fm_str}. Cause: {mr.root_cause or 'N/A'}. Action: {mr.corrective_action or 'N/A'}"
                    items.append(
                        EvidenceItem(
                            evidence_id=ev_id,
                            content=content_str,
                            equipment_tag=mr.equipment_tag,
                            document_id=mr.document_id,
                            document_type=str(mr.document_type),
                            source=mr.source,
                            relevance_score=0.85,
                            evidence_type="maintenance_event",
                            metadata={"event_id": mr.event_id, "downtime_hours": mr.downtime_hours, "parts": mr.parts_replaced}
                        )
                    )

        # Sort items: highest relevance first
        items.sort(key=lambda x: x.relevance_score, reverse=True)

        return EvidencePackage(
            query=understanding.query,
            equipment_tag=tag,
            intent=understanding.intent,
            items=items,
            sufficiency=sufficiency.status,
            sufficiency_reason=sufficiency.reason,
            covered_knowledge_types=sufficiency.covered_knowledge_types,
            uncovered_knowledge_types=sufficiency.uncovered_knowledge_types,
            conflicts=getattr(sufficiency, "conflicts", [])
        )

