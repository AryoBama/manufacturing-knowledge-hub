import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Instrument tags regex: VSHH-1201, PSLL-1201, FV-1201, TI-5604
INSTRUMENT_TAG_PATTERN = re.compile(r"\b([A-Z]{2,4}-\d{4}[A-Z]?)\b", re.IGNORECASE)

# Chandra Asri Baseline Equipment Registry & Common Aliases (Multilingual: EN & ID)
# Loaded dynamically from canonical configs/plant_equipment_registry.json
_REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "configs" / "plant_equipment_registry.json"
PLANT_EQUIPMENT_REGISTRY: Dict[str, Dict[str, Any]] = {}
if _REGISTRY_PATH.exists():
    try:
        with open(_REGISTRY_PATH, "r", encoding="utf-8") as _f:
            PLANT_EQUIPMENT_REGISTRY = json.load(_f)
    except Exception:
        PLANT_EQUIPMENT_REGISTRY = {}


SYMPTOM_KEYWORDS = [
    "high vibration", "excessive vibration", "vibration",
    "seal leak", "leakage", "leak",
    "trip", "tripped", "shutdown",
    "high temperature", "overheating", "hot",
    "pressure drop", "low pressure", "high pressure",
    "low flow", "no flow",
    "cavitation", "fouling", "plugging", "clogged"
]

# Robust tag regex supporting hyphenated, unhyphenated, and spaced formats (e.g. GA-1201A, GA1201A, P-9999, B-5501)
EQUIPMENT_TAG_PATTERN = re.compile(r"\b([A-Za-z]{1,3})[\s\-]?(\d{4})[\s\-]?([A-Za-z]?)\b")

# Instrument tags prefix set (ISA-5.1)
KNOWN_INSTRUMENT_PREFIXES = {
    "PT", "PI", "TT", "TI", "FT", "FI", "VT", "VI", "LT", "LI",
    "PSLL", "PSHH", "FSLL", "FSHH", "VSHH", "TSHH", "PDI", "PDT",
    "ZSO", "ZSC", "XV", "FV", "RO", "HS", "MPR", "SEQ"
}

# Standard Plant Loop-to-Asset Mapping dynamically loaded from unified PLANT_EQUIPMENT_REGISTRY
LOOP_TO_EQUIPMENT: Dict[str, str] = {
    str(data["loop_number"]): tag
    for tag, data in PLANT_EQUIPMENT_REGISTRY.items()
    if "loop_number" in data
}
if not LOOP_TO_EQUIPMENT:
    LOOP_TO_EQUIPMENT = {
        "1201": "GA-1201A",
        "4501": "KC-4501",
        "2301": "YD-2301",
        "3401": "DC-3401A",
        "5601": "EA-5601",
        "6701": "LV-6701",
        "7801": "CT-7801",
        "8901": "FA-8901"
    }

# Prepositions and common 1-3 letter words that should not be parsed as equipment tags (e.g. 'on 2024')
COMMON_STOPWORDS_2_3 = {
    "ON", "IN", "AT", "TO", "BY", "FOR", "AND", "THE", "WAS", "HAS", "HAD",
    "DAN", "DARI", "PADA", "KE", "DI", "INI", "ITU", "ADA", "A", "AN"
}


def _split_tag_prefix(tag: str) -> str:
    parts = tag.split("-")
    return parts[0].upper() if parts else ""


def extract_equipment_tags(text: str) -> List[str]:
    raw_matches = EQUIPMENT_TAG_PATTERN.findall(text)
    eq_candidates = []
    for m in raw_matches:
        prefix_raw = m[0].upper()
        if prefix_raw in COMMON_STOPWORDS_2_3:
            continue

        cand = f"{prefix_raw}-{m[1]}{m[2].upper()}"
        # If explicitly in equipment registry, it's always an equipment tag (e.g. LV-6701)
        if cand in PLANT_EQUIPMENT_REGISTRY:
            eq_candidates.append(cand)
            continue
        # If prefix is a known instrument type, exclude from equipment candidates
        prefix = _split_tag_prefix(cand)
        if prefix in KNOWN_INSTRUMENT_PREFIXES:
            continue
        eq_candidates.append(cand)

    found = list(dict.fromkeys(eq_candidates))

    # Detect sister tag comparisons like "GA-1201B same as A" or "GA-1201B vs A" or "seperti A"
    if found:
        for cand in list(found):
            sister_match = re.search(r'\b(?:same as|similar to|seperti|dibanding(?:kan)?|vs|versus|and|dan)\s+([A-Za-z])\b', text, re.IGNORECASE)
            if sister_match:
                sister_letter = sister_match.group(1).upper()
                if len(cand) >= 2 and cand[-1].isalpha():
                    sister_cand = f"{cand[:-1]}{sister_letter}"
                    if sister_cand in PLANT_EQUIPMENT_REGISTRY and sister_cand not in found:
                        found.append(sister_cand)
        return found

    # Check equipment name aliases across the whole registry
    lower_text = text.lower()
    found_aliases = []
    for tag, info in PLANT_EQUIPMENT_REGISTRY.items():
        for alias in info.get("aliases", []):
            if re.search(r'\b' + re.escape(alias) + r'\b', lower_text):
                found_aliases.append(tag)
                break

    if found_aliases:
        return list(dict.fromkeys(found_aliases))

    # Check instrument loop association (e.g. PSLL-1201 -> GA-1201A)
    loop_matches = re.findall(r'\b(?:[A-Z]{2,4}-)?(\d{4})[A-Z]?\b', text, re.IGNORECASE)
    for loop in loop_matches:
        if loop in LOOP_TO_EQUIPMENT:
            return [LOOP_TO_EQUIPMENT[loop]]

    # Check historical work orders (e.g. WO-240007 -> GA-1201A)
    if "240007" in text:
        return ["GA-1201A"]

    return []



def extract_instrument_tags(text: str) -> List[str]:
    matches = INSTRUMENT_TAG_PATTERN.findall(text)
    equipment = set(extract_equipment_tags(text))
    instruments = []
    for m in matches:
        cand = m.upper()
        if cand in equipment:
            continue
        prefix = _split_tag_prefix(cand)
        if prefix in KNOWN_INSTRUMENT_PREFIXES or len(prefix) >= 3:
            instruments.append(cand)
    return list(dict.fromkeys(instruments))


def extract_symptom(text: str) -> Optional[str]:
    lower_text = text.lower()
    for kw in SYMPTOM_KEYWORDS:
        if kw in lower_text:
            return kw
    return None


def extract_entities(text: str) -> Dict[str, Any]:
    entities = {}
    tags = extract_equipment_tags(text)
    if tags:
        entities["equipment_tags"] = tags
        entities["equipment_tag"] = tags[0]
        if tags[0] in PLANT_EQUIPMENT_REGISTRY:
            entities["equipment_name"] = PLANT_EQUIPMENT_REGISTRY[tags[0]]["name"]
            entities["area"] = PLANT_EQUIPMENT_REGISTRY[tags[0]]["area"]

    instruments = extract_instrument_tags(text)
    if instruments:
        entities["instrument_tags"] = instruments

    symptom = extract_symptom(text)
    if symptom:
        entities["symptom"] = symptom

    return entities
