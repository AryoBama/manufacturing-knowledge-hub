import json
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from schemas.technical import TechnicalRecord
from schemas.relationship import RelationshipRecord
from schemas.maintenance import MaintenanceRecord
from src.ingestion.metadata import find_canonical_field, resolve_equipment


class StructuredKnowledgeStore:
    """
    Step 16: Structured Knowledge Store for Phase 2 Integration.
    Enables deterministic lookup of TechnicalRecords, RelationshipRecords, and MaintenanceRecords
    alongside textual DocumentChunks.
    """
    def __init__(
        self,
        technical_records: Optional[List[TechnicalRecord]] = None,
        relationships: Optional[List[RelationshipRecord]] = None,
        maintenance_records: Optional[List[MaintenanceRecord]] = None
    ):
        self.technical_records = technical_records or []
        self.relationships = relationships or []
        self.maintenance_records = maintenance_records or []

        # Indexes
        self._tech_by_tag = defaultdict(list)
        self._tech_by_canon = defaultdict(list)
        for tr in self.technical_records:
            if tr.equipment_tag:
                self._tech_by_tag[tr.equipment_tag.upper()].append(tr)
            if tr.canonical_field:
                self._tech_by_canon[(tr.equipment_tag or "").upper(), tr.canonical_field.lower()].append(tr)

        self._rel_by_target = defaultdict(list)
        self._rel_by_source = defaultdict(list)
        for rel in self.relationships:
            if rel.target_tag:
                self._rel_by_target[rel.target_tag.upper()].append(rel)
            if rel.source_tag:
                self._rel_by_source[rel.source_tag.upper()].append(rel)

        self._mnt_by_tag = defaultdict(list)
        for mr in self.maintenance_records:
            if mr.equipment_tag:
                self._mnt_by_tag[mr.equipment_tag.upper()].append(mr)

    @classmethod
    def load_from_processed_dir(cls, processed_dir: Path) -> "StructuredKnowledgeStore":
        """
        Loads all structured objects from data/processed/ directory.
        """
        trs: List[TechnicalRecord] = []
        rels: List[RelationshipRecord] = []
        mrs: List[MaintenanceRecord] = []

        if not processed_dir.exists():
            return cls([], [], [])

        for json_file in processed_dir.rglob("*.json"):
            fname = json_file.name.lower()
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data if isinstance(data, list) else [data]

                if "technical_records" in fname:
                    for it in items:
                        if isinstance(it, dict) and "record_id" in it:
                            trs.append(TechnicalRecord.model_validate(it))
                elif "relationships" in fname:
                    for it in items:
                        if isinstance(it, dict) and "relationship_id" in it:
                            rels.append(RelationshipRecord.model_validate(it))
                elif "maintenance" in fname:
                    for it in items:
                        if isinstance(it, dict) and "event_id" in it:
                            mrs.append(MaintenanceRecord.model_validate(it))
            except Exception as e:
                print(f"[WARN] Error loading {json_file}: {e}")

        return cls(technical_records=trs, relationships=rels, maintenance_records=mrs)

    def lookup_technical_parameter(
        self,
        equipment_tag: str,
        parameter_query: str
    ) -> List[TechnicalRecord]:
        """
        Looks up a parameter (e.g. 'Rated Flow', 'rated_flow', 'speed', 'motor power')
        for a specific equipment tag.
        """
        tag_upper = equipment_tag.upper()
        res = resolve_equipment(equipment_tag)
        if res.get("status") == "resolved":
            tag_upper = res["equipment_tag"]

        param_clean = parameter_query.strip().lower()
        canon_field, _ = find_canonical_field(param_clean)

        matches: List[TechnicalRecord] = []
        # Check canonical index
        if canon_field and (tag_upper, canon_field) in self._tech_by_canon:
            matches.extend(self._tech_by_canon[tag_upper, canon_field])

        # Check parameter text match
        candidates = self._tech_by_tag.get(tag_upper, [])
        for tr in candidates:
            if tr in matches:
                continue
            if (
                param_clean in tr.parameter.lower()
                or tr.parameter.lower() in param_clean
                or (tr.canonical_field and tr.canonical_field.lower() in param_clean)
            ):
                matches.append(tr)

        return matches

    def lookup_relationships(
        self,
        equipment_tag: str,
        relationship_type: Optional[str] = None,
        context_keyword: Optional[str] = None
    ) -> List[RelationshipRecord]:
        """
        Looks up relationship records (e.g. triggers_trip, permissive_for)
        connected to the equipment.
        """
        tag_upper = equipment_tag.upper()
        res = resolve_equipment(equipment_tag)
        if res.get("status") == "resolved":
            tag_upper = res["equipment_tag"]

        # Entities targeting this equipment
        candidates = self._rel_by_target.get(tag_upper, []) + self._rel_by_source.get(tag_upper, [])
        dedup_candidates = list({r.relationship_id: r for r in candidates}.values())

        filtered = []
        for rel in dedup_candidates:
            if relationship_type and rel.relationship.lower() != relationship_type.lower():
                continue
            if context_keyword:
                ctx = (rel.context or "").lower()
                if context_keyword.lower() not in ctx:
                    continue
            filtered.append(rel)

        return filtered

    def lookup_maintenance(
        self,
        equipment_tag: str,
        symptom_keyword: Optional[str] = None
    ) -> List[MaintenanceRecord]:
        """
        Looks up maintenance history for equipment, optionally filtering by symptom keyword.
        """
        tag_upper = equipment_tag.upper()
        res = resolve_equipment(equipment_tag)
        if res.get("status") == "resolved":
            tag_upper = res["equipment_tag"]

        records = self._mnt_by_tag.get(tag_upper, [])
        if not symptom_keyword:
            return records

        kw = symptom_keyword.lower()
        matched = []
        for mr in records:
            blob = f"{mr.symptom or ''} {mr.root_cause or ''} {mr.corrective_action or ''}".lower()
            if kw in blob:
                matched.append(mr)

        return matched
