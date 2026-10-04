import json
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from schemas.technical import TechnicalRecord
from schemas.relationship import RelationshipRecord
from schemas.maintenance import MaintenanceRecord
from src.ingestion.metadata import find_canonical_field, resolve_equipment


def clean_token(token: str) -> str:
    """Strips punctuation and trailing dots/colons from token."""
    import re
    return re.sub(r'^[^\w]+|[^\w]+$', '', token.lower())


def token_prefix_match(t1: str, t2: str, min_len: int = 3) -> bool:
    """
    Algorithmic match without hardcoded keyword dictionaries:
    Two tokens match if:
    1. Exact equality (e.g. 'flow' == 'flow')
    2. One is a prefix of the other with length >= min_len (e.g. 'temp' matches 'temperature', 'press' matches 'pressure')
    """
    a = clean_token(t1)
    b = clean_token(t2)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= min_len and len(b) >= min_len:
        return a.startswith(b) or b.startswith(a)
    return False


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

    def get_technical_records_by_tag(self, equipment_tag: str) -> List[TechnicalRecord]:
        """
        Returns all structured technical parameters for an equipment tag.
        """
        tag_upper = equipment_tag.upper()
        res = resolve_equipment(equipment_tag)
        if res.get("status") == "resolved":
            tag_upper = res["equipment_tag"]
        return list(self._tech_by_tag.get(tag_upper, []))

    def lookup_technical_parameter(
        self,
        equipment_tag: str,
        parameter_query: str
    ) -> List[TechnicalRecord]:
        """
        Looks up a parameter (e.g. 'Rated Flow', 'rated_flow', 'speed', 'design temperature', 'pressure')
        for a specific equipment tag using dynamic token prefix matching.
        """
        import re
        tag_upper = equipment_tag.upper()
        res = resolve_equipment(equipment_tag)
        if res.get("status") == "resolved":
            tag_upper = res["equipment_tag"]

        param_clean = parameter_query.strip().lower()
        matches: List[TechnicalRecord] = []

        # 1. Check canonical field index directly
        canon_field, _ = find_canonical_field(param_clean)
        if canon_field and (tag_upper, canon_field) in self._tech_by_canon:
            for tr in self._tech_by_canon[tag_upper, canon_field]:
                if tr not in matches:
                    matches.append(tr)

        # 2. Dynamic token prefix matching across candidate parameters
        candidates = self._tech_by_tag.get(tag_upper, [])
        query_tokens = [clean_token(w) for w in re.findall(r'\b[a-zA-Z0-9_-]+\b', param_clean) if len(clean_token(w)) >= 3]

        for tr in candidates:
            if tr in matches:
                continue
            tr_param = tr.parameter.lower()
            tr_canon = (tr.canonical_field or "").lower()

            # Exact or substring match
            if (
                param_clean in tr_param
                or tr_param in param_clean
                or (tr_canon and (param_clean in tr_canon or tr_canon in param_clean))
            ):
                matches.append(tr)
                continue

            # Token-level prefix match
            param_tokens = [clean_token(w) for w in re.findall(r'\b[a-zA-Z0-9_-]+\b', tr_param) if len(clean_token(w)) >= 3]
            canon_tokens = [clean_token(w) for w in re.findall(r'\b[a-zA-Z0-9_-]+\b', tr_canon) if len(clean_token(w)) >= 3]
            all_target_tokens = param_tokens + canon_tokens

            if any(
                token_prefix_match(qt, tt, min_len=3)
                for qt in query_tokens
                for tt in all_target_tokens
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
