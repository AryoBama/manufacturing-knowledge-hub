import re
from typing import List, Dict, Any, Optional, Tuple
from schemas.common import DocumentSource, DocumentStatus, DocumentType
from schemas.governance import ConflictRecord, ConflictType
from src.retrieval.models import RetrievalResult


# Authority ranking by document category (higher = more authoritative for engineering limits)
DOCUMENT_AUTHORITY = {
    "INTERLOCK": 1.0,
    "DATASHEET": 0.95,
    "PID": 0.90,
    "SOP": 0.80,
    "OPL": 0.60,
    "MAINTENANCE": 0.70,
    "OTHER": 0.40,
    "UNKNOWN": 0.10
}

# Status authority ranking
STATUS_AUTHORITY = {
    DocumentStatus.ISSUED_FOR_OPERATION: 1.0,
    DocumentStatus.APPROVED: 0.9,
    DocumentStatus.ISSUED_FOR_CONSTRUCTION: 0.8,
    DocumentStatus.ISSUED_FOR_REVIEW: 0.5,
    DocumentStatus.UNDER_REVIEW: 0.4,
    DocumentStatus.DRAFT: 0.2,
    DocumentStatus.SUPERSEDED: 0.1,
    DocumentStatus.OBSOLETE: 0.0,
    DocumentStatus.UNKNOWN: 0.1
}


def normalize_unit_value(val: float, unit: str) -> Tuple[float, str]:
    """
    Normalizes engineering units to base SI equivalents to avoid false conflicts
    between equivalent expressions (e.g., 800 mbar vs 0.8 bar).
    """
    u = unit.lower().replace("³", "3").strip()

    # Pressure normalization to 'bar'
    if u in ["bar", "barg"]:
        return val, "bar"
    if u in ["mbar", "mbarg"]:
        return val * 0.001, "bar"
    if u in ["kpa"]:
        return val * 0.01, "bar"
    if u in ["mpa"]:
        return val * 10.0, "bar"
    if u in ["psi", "psig"]:
        return val * 0.0689476, "bar"

    # Flow normalization to 'm3/h'
    if u in ["m3/h", "m3/hr", "cum/hr", "m3h"]:
        return val, "m3/h"
    if u in ["l/min", "lpm"]:
        return val * 0.06, "m3/h"
    if u in ["gpm"]:
        return val * 0.227124, "m3/h"

    # Power normalization to 'kw'
    if u in ["kw"]:
        return val, "kw"
    if u in ["hp"]:
        return val * 0.7457, "kw"

    # Head / length normalization to 'm'
    if u in ["m", "meter", "meters"]:
        return val, "m"
    if u in ["ft", "feet"]:
        return val * 0.3048, "m"

    return val, u


def are_values_equivalent(val_a: float, unit_a: str, val_b: float, unit_b: str, max_relative_delta: float = 0.01) -> bool:
    """
    Returns True if two values are technically equivalent under unit conversion.
    e.g. 800 mbar vs 0.8 bar -> True (delta = 0.0)
    """
    norm_a, base_u_a = normalize_unit_value(val_a, unit_a)
    norm_b, base_u_b = normalize_unit_value(val_b, unit_b)
    if base_u_a != base_u_b:
        return False
    max_val = max(abs(norm_a), abs(norm_b), 1e-6)
    delta = abs(norm_a - norm_b) / max_val
    return delta <= max_relative_delta


class ConflictDetector:
    """
    Priority 1: Conflict Detection & Resolution Engine.
    Detects contradictions between authoritative plant documents (numeric setpoints,
    superseded revisions, operational limits) without forcing artificial choices.
    """

    @classmethod
    def detect_conflicts(
        cls,
        results: List[RetrievalResult],
        equipment_tag: Optional[str] = None
    ) -> List[ConflictRecord]:
        conflicts: List[ConflictRecord] = []

        if len(results) < 2:
            return conflicts

        # 1. Detect Revision Lineage / Superseded Conflicts
        rev_conflicts = cls._detect_revision_conflicts(results)
        conflicts.extend(rev_conflicts)

        # 2. Detect Numeric Setpoint Contradictions
        num_conflicts = cls._detect_numeric_conflicts(results, equipment_tag)
        conflicts.extend(num_conflicts)

        return conflicts

    @classmethod
    def _detect_revision_conflicts(cls, results: List[RetrievalResult]) -> List[ConflictRecord]:
        conflicts = []
        doc_families: Dict[str, List[RetrievalResult]] = {}
        for r in results:
            family_key = r.document_id.split("-REV")[0].split("-P0")[0]
            doc_families.setdefault(family_key, []).append(r)

        for fam, items in doc_families.items():
            if len(items) > 1:
                # Check if multiple differing revisions or superseded status present
                revisions = {item.source.revision for item in items if item.source.revision}
                statuses = {item.source.status for item in items if item.source.status}
                if len(revisions) > 1 or DocumentStatus.SUPERSEDED in statuses or DocumentStatus.OBSOLETE in statuses:
                    item_a = items[0]
                    item_b = items[1]
                    conflicts.append(ConflictRecord(
                        conflict_type=ConflictType.REVISION_CONFLICT,
                        entity_tag=item_a.equipment_tag or item_b.equipment_tag,
                        parameter_name="document_revision_status",
                        source_a=item_a.source,
                        value_a=f"Rev: {item_a.source.revision} ({item_a.source.status})",
                        source_b=item_b.source,
                        value_b=f"Rev: {item_b.source.revision} ({item_b.source.status})",
                        resolution_status="REVISION_RESOLVED" if item_a.source.status != item_b.source.status else "UNRESOLVED",
                        recommended_action="Superseded document detected. Exclude superseded version and adhere to the active Issued for Operation revision."
                    ))
        return conflicts

    @classmethod
    def _detect_numeric_conflicts(
        cls,
        results: List[RetrievalResult],
        equipment_tag: Optional[str] = None
    ) -> List[ConflictRecord]:
        conflicts = []
        # Regex to extract tag setpoints: e.g. "PSLL-1201 < 0.5 barg" vs "PSLL-1201 < 0.8 barg"
        setpoint_pattern = re.compile(
            r"\b([A-Z]{2,4}-\d{4}[A-Z]?)\b[^\d\n\r]{0,30}([<>]=?|\bmin\b|\bmax\b|\bset\b|\bat\b)?\s*([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z³/]+)",
            re.IGNORECASE
        )

        extracted_claims: Dict[str, List[Tuple[float, str, RetrievalResult]]] = {}

        for r in results:
            text = r.content
            matches = setpoint_pattern.findall(text)
            for m in matches:
                tag = m[0].upper()
                try:
                    val = float(m[2])
                    unit = m[3].lower()
                    extracted_claims.setdefault(tag, []).append((val, unit, r))
                except ValueError:
                    continue

        for tag, occurrences in extracted_claims.items():
            if len(occurrences) >= 2:
                # Compare pairs
                first_val, first_unit, first_res = occurrences[0]
                norm_first_val, base_u_first = normalize_unit_value(first_val, first_unit)

                for val, unit, res in occurrences[1:]:
                    if first_res.document_id == res.document_id:
                        continue

                    norm_val, base_u_val = normalize_unit_value(val, unit)

                    # Only compare if normalized units belong to the same physical dimension
                    if base_u_first == base_u_val:
                        max_val = max(abs(norm_first_val), abs(norm_val), 1e-6)
                        delta = abs(norm_first_val - norm_val) / max_val

                        # If relative delta > 1%, genuine contradiction exists across documents
                        if delta > 0.01:
                            conflicts.append(ConflictRecord(
                                conflict_type=ConflictType.NUMERIC_CONFLICT,
                                entity_tag=tag,
                                parameter_name=f"Operational limit / setpoint for {tag}",
                                source_a=first_res.source,
                                value_a=f"{first_val} {first_unit} ({first_res.document_type}: {first_res.document_id})",
                                source_b=res.source,
                                value_b=f"{val} {unit} ({res.document_type}: {res.document_id})",
                                resolution_status="UNRESOLVED",
                                recommended_action=f"Contradictory values found for {tag} ({first_val} {first_unit} vs {val} {unit}). Do not assume either value. Verify against certified DCS C&E matrix."
                            ))

        return conflicts
