import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

from schemas.common import DocumentStatus, DocumentType

# Load semantic mapping if available
SEMANTIC_MAPPING_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "semantic_mapping.json"
_SEMANTIC_DATA: Dict[str, Any] = {}
if SEMANTIC_MAPPING_PATH.exists():
    try:
        with open(SEMANTIC_MAPPING_PATH, "r", encoding="utf-8") as f:
            _SEMANTIC_DATA = json.load(f)
    except Exception:
        _SEMANTIC_DATA = {}


# STEP 7: Document Type Normalization Mapping
DOCUMENT_TYPE_MAP = {
    "datasheet": DocumentType.DATASHEET,
    "equipment datasheet": DocumentType.DATASHEET,
    "data sheet": DocumentType.DATASHEET,
    "ds": DocumentType.DATASHEET,
    "opl": DocumentType.OPL,
    "one point lesson": DocumentType.OPL,
    "operating procedure": DocumentType.OPL,
    "sop": DocumentType.SOP,
    "standard operating procedure": DocumentType.SOP,
    "pid": DocumentType.PID,
    "p&id": DocumentType.PID,
    "piping & instrumentation diagram": DocumentType.PID,
    "piping and instrumentation diagram": DocumentType.PID,
    "process piping diagram": DocumentType.PID,
    "interlock": DocumentType.INTERLOCK,
    "interlock logic": DocumentType.INTERLOCK,
    "cause & effect": DocumentType.INTERLOCK,
    "cause effect": DocumentType.INTERLOCK,
    "cause and effect": DocumentType.INTERLOCK,
    "shutdown logic": DocumentType.INTERLOCK,
    "plot plan": DocumentType.PLOT_PLAN,
    "equipment location": DocumentType.PLOT_PLAN,
    "plant layout": DocumentType.PLOT_PLAN,
    "layout": DocumentType.PLOT_PLAN,
    "ga drawing": DocumentType.GA_DRAWING,
    "general arrangement": DocumentType.GA_DRAWING,
    "maintenance": DocumentType.MAINTENANCE,
    "maintenance history": DocumentType.MAINTENANCE,
    "sap pm": DocumentType.MAINTENANCE,
    "cmms": DocumentType.MAINTENANCE,
    "work order": DocumentType.MAINTENANCE
}


def normalize_document_type(raw_type: Union[str, DocumentType, None]) -> Tuple[DocumentType, Optional[str]]:
    """
    Normalizes a document type string or enum to canonical DocumentType.
    Returns (canonical_enum, warning_if_unknown).
    """
    if raw_type is None:
        return DocumentType.UNKNOWN, "Document type is missing (None)"

    if isinstance(raw_type, DocumentType):
        return raw_type, None

    cleaned = str(raw_type).strip().lower()
    if cleaned in DOCUMENT_TYPE_MAP:
        return DOCUMENT_TYPE_MAP[cleaned], None

    # Partial containment search
    for k, v in DOCUMENT_TYPE_MAP.items():
        if k in cleaned or cleaned in k:
            return v, None

    return DocumentType.UNKNOWN, f"Unknown document type label: '{raw_type}'"


# STEP 8: Source Metadata Normalization
STATUS_MAP = {
    "approved": DocumentStatus.APPROVED,
    "appr": DocumentStatus.APPROVED,
    "issued for operation": DocumentStatus.ISSUED_FOR_OPERATION,
    "ifo": DocumentStatus.ISSUED_FOR_OPERATION,
    "issued for construction": DocumentStatus.ISSUED_FOR_CONSTRUCTION,
    "ifc": DocumentStatus.ISSUED_FOR_CONSTRUCTION,
    "issued for review": DocumentStatus.ISSUED_FOR_REVIEW,
    "ifr": DocumentStatus.ISSUED_FOR_REVIEW,
    "draft": DocumentStatus.DRAFT,
    "obsolete": DocumentStatus.OBSOLETE
}


def normalize_status(raw_status: Optional[str]) -> Optional[DocumentStatus]:
    """
    Normalizes document status without hallucinating missing data.
    If None or empty, returns None.
    """
    if not raw_status:
        return None
    cleaned = str(raw_status).strip().lower()
    return STATUS_MAP.get(cleaned, DocumentStatus.UNKNOWN)


def normalize_revision(raw_rev: Optional[str]) -> Optional[str]:
    """
    Normalizes revision strings:
    'Rev 3', 'REV.03', 'Revision 3' -> 'Rev.03'
    'Rev 0' -> 'Rev.00'
    'Rev B' -> 'Rev.B'
    If None or empty, returns None.
    """
    if not raw_rev:
        return None
    s = str(raw_rev).strip()
    if s.lower() in ("none", "null", "-", "—", ""):
        return None

    # Check for numeric revision
    match_num = re.search(r"(\d+)", s)
    if match_num:
        num = int(match_num.group(1))
        return f"Rev.{num:02d}"

    # Check for letter revision (e.g. Rev A, Rev B)
    match_letter = re.search(r"\b([A-Za-z])\b", s)
    if match_letter:
        return f"Rev.{match_letter.group(1).upper()}"

    return s


def normalize_unit(raw_unit: Optional[str]) -> Optional[str]:
    """
    Normalizes engineering units to standardized symbols.
    """
    if not raw_unit:
        return None
    u = str(raw_unit).strip()
    if u in ("-", "—", "None", "null", ""):
        return None

    unit_map = {
        "m³/h": "m3/h",
        "m3/h": "m3/h",
        "m^3/h": "m3/h",
        "m3/hr": "m3/h",
        "m³/hr": "m3/h",
        "degc": "degC",
        "°c": "degC",
        "c": "degC",
        "kw": "kW",
        "bar": "bar",
        "barg": "barg",
        "rpm": "rpm",
        "m": "m",
        "mm/s": "mm/s",
        "mm/s rms": "mm/s RMS",
        "cp": "cP",
        "v": "V",
        "a": "A",
        "hz": "Hz",
        "kg": "kg"
    }
    return unit_map.get(u.lower(), u)


# STEP 6: Equipment Resolution
# Loaded dynamically from canonical configs/plant_equipment_registry.json
_PLANT_REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "configs" / "plant_equipment_registry.json"
EQUIPMENT_REGISTRY: Dict[str, Dict[str, Any]] = {}
if _PLANT_REGISTRY_PATH.exists():
    try:
        with open(_PLANT_REGISTRY_PATH, "r", encoding="utf-8") as _f:
            EQUIPMENT_REGISTRY = json.load(_f)
    except Exception:
        EQUIPMENT_REGISTRY = {}


AMBIGUOUS_KEYWORDS = {
    "feed pump": ["GA-1201A", "GA-1201B"],
    "pompa feed": ["GA-1201A", "GA-1201B"],
    "hexane pump": ["GA-1201A", "GA-1201B"],
    "pompa hexane": ["GA-1201A"],  # Defaults to primary A if exact, but handled below
}


def resolve_equipment(input_str: Optional[str]) -> Dict[str, Any]:
    """
    Step 6: Equipment Resolution.
    Maps arbitrary input (tags, aliases, colloquial names) to canonical equipment tag.
    Returns:
    - { 'status': 'resolved', 'equipment_tag': 'GA-1201A', 'confidence': 'high', 'type': '...' }
    - { 'status': 'ambiguous', 'candidates': ['GA-1201A', 'GA-1201B'], 'confidence': 'low' }
    - { 'status': 'unknown', 'equipment_tag': None, 'confidence': 'none' }
    """
    if not input_str:
        return {"status": "unknown", "equipment_tag": None, "confidence": "none"}

    s = input_str.strip()
    s_upper = s.upper()
    s_lower = s.lower()

    # Exact Canonical Tag Match
    if s_upper in EQUIPMENT_REGISTRY:
        return {
            "status": "resolved",
            "equipment_tag": s_upper,
            "confidence": "high",
            "type": EQUIPMENT_REGISTRY[s_upper]["type"]
        }

    # Normalized Tag Regex Match (e.g. GA1201A -> GA-1201A)
    norm_tag = re.sub(r"([A-Z]{2})(\d{4})([A-Z]?)", r"\1-\2\3", s_upper)
    if norm_tag in EQUIPMENT_REGISTRY:
        return {
            "status": "resolved",
            "equipment_tag": norm_tag,
            "confidence": "high",
            "type": EQUIPMENT_REGISTRY[norm_tag]["type"]
        }

    # Check for Ambiguous Generic Names First
    for kw, candidates in AMBIGUOUS_KEYWORDS.items():
        if kw == s_lower:
            if len(candidates) > 1:
                return {
                    "status": "ambiguous",
                    "equipment_tag": None,
                    "confidence": "low",
                    "candidates": candidates
                }

    # Search through Registry Aliases
    matched_tags = set()
    for tag, info in EQUIPMENT_REGISTRY.items():
        for alias in info["aliases"]:
            if alias == s_lower or alias in s_lower:
                matched_tags.add(tag)

    if len(matched_tags) == 1:
        resolved_tag = list(matched_tags)[0]
        return {
            "status": "resolved",
            "equipment_tag": resolved_tag,
            "confidence": "high" if s_lower in EQUIPMENT_REGISTRY[resolved_tag]["aliases"] else "medium",
            "type": EQUIPMENT_REGISTRY[resolved_tag]["type"]
        }
    elif len(matched_tags) > 1:
        return {
            "status": "ambiguous",
            "equipment_tag": None,
            "confidence": "low",
            "candidates": sorted(list(matched_tags))
        }

    return {"status": "unknown", "equipment_tag": None, "confidence": "none"}


def find_canonical_field(source_label: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Looks up canonical_field and standard_unit for a given source label using schemas/semantic_mapping.json.
    Returns (canonical_field, standard_unit).
    """
    clean_lbl = source_label.strip().lower()
    for mapping in _SEMANTIC_DATA.get("mappings", []):
        for candidate in mapping.get("source_labels", []):
            if candidate.strip().lower() == clean_lbl:
                return mapping["canonical_field"], mapping.get("standard_unit")
    return None, None
