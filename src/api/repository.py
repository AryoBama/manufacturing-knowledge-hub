import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.pipeline import ManufacturingKnowledgeHub

router = APIRouter(prefix="/api/repository", tags=["Knowledge Repository"])

_REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "configs" / "plant_equipment_registry.json"
_HIERARCHY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge" / "hierarchy.json"

PLANT_NAME = "Chandra Asri Petrochemical Complex Cilegon"


def _get_hub() -> ManufacturingKnowledgeHub:
    # Imported lazily to share the singleton owned by the main router.
    from src.api.routes import get_hub
    return get_hub()


def _load_json(path: Path) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _enum_value(v: Any) -> Optional[str]:
    if v is None:
        return None
    return str(getattr(v, "value", v))


def _group_documents(hub: ManufacturingKnowledgeHub) -> Dict[tuple, List[Any]]:
    groups: Dict[tuple, List[Any]] = defaultdict(list)
    for chunk in hub.registry.get_all():
        groups[(chunk.document_id, (chunk.equipment_tag or "").upper())].append(chunk)
    return groups


def _summarize(key: tuple, chunks: List[Any], registry: Dict[str, Any]) -> Dict[str, Any]:
    first = chunks[0]
    tag = key[1] or None
    equip = registry.get(tag or "", {})
    return {
        "document_id": first.document_id,
        "title": first.title,
        "document_type": _enum_value(first.document_type),
        "equipment_tag": tag,
        "equipment_name": equip.get("name"),
        "area": equip.get("area"),
        "file_name": first.source.file_name,
        "revision": first.source.revision,
        "status": _enum_value(first.source.status),
        "chunk_count": len(chunks),
    }


_SYMBOL_BY_TYPE = [
    ("pump", "pump"),
    ("compressor", "compressor"),
    ("dryer", "dryer"),
    ("reactor", "reactor"),
    ("exchanger", "exchanger"),
    ("control valve", "control_valve"),
    ("cooling tower", "cooling_tower"),
    ("distillation", "column"),
]


def _symbol_for(equipment_type: Optional[str]) -> str:
    t = (equipment_type or "").lower()
    return next((sym for key, sym in _SYMBOL_BY_TYPE if key in t), "vessel")


def _rel_value(rel: Any, field: str) -> Any:
    return getattr(rel, field, None)


def _parse_context(context: str) -> Dict[str, Optional[str]]:
    """Pulls setpoint / voting out of strings like 'Suction Pressure LOW-LOW (Setpoint: < 0.5 barg, Voting: 2oo3)'."""
    setpoint = re.search(r"Setpoint:\s*([^,)]+)", context or "")
    voting = re.search(r"Voting:\s*([0-9A-Za-z]+)", context or "")
    return {
        "setpoint": setpoint.group(1).strip() if setpoint else None,
        "voting": voting.group(1).strip() if voting else None,
    }


def _target_kind(tag: str) -> str:
    t = tag.upper()
    if t.startswith("DCS"):
        return "system"
    if t.startswith(("FV", "LV", "PV", "TV")):
        return "control_valve"
    if t.startswith(("XV", "ZV", "HV")):
        return "valve"
    if t.startswith("GA"):
        return "pump"
    if t.startswith("KC"):
        return "compressor"
    return "other"


def _interlock_view(rels: List[Any], equipment_tag: Optional[str]) -> Dict[str, Any]:
    trips, permissives = [], []
    for r in rels:
        meta = r.metadata or {}
        rtype = str(getattr(r.relationship, "value", r.relationship))
        parsed = _parse_context(r.context or "")
        if rtype == "triggers_trip":
            actions = meta.get("actions") or []
            targets = meta.get("targets") or []
            effects = []
            for i, action in enumerate(actions):
                tag = targets[i] if len(targets) == len(actions) else None
                effects.append({"action": action, "target": tag, "kind": _target_kind(tag) if tag else "other"})
            trips.append({
                "id": meta.get("trip_id"),
                "initiator": r.source_tag,
                "description": r.context,
                "setpoint": parsed["setpoint"],
                "voting": parsed["voting"],
                "sil": meta.get("sil_level"),
                "effects": effects,
            })
        elif rtype == "permissive_for":
            permissives.append({
                "id": meta.get("permissive_id"),
                "source": r.source_tag,
                "description": r.context,
                "gate": meta.get("gate"),
            })
    return {"trips": trips, "permissives": permissives}


def _opl_sections(content: str) -> Dict[str, Any]:
    """Splits OPL text into its CAPS-headed sections; lines before the first heading are the header block."""
    header: List[str] = []
    sections: List[Dict[str, Any]] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.fullmatch(r"[A-Z][A-Z0-9 &/()\-]+:", line):
            sections.append({"title": line[:-1].title(), "lines": []})
        elif sections:
            sections[-1]["lines"].append(re.sub(r"^-\s*", "", line))
        else:
            header.append(line)
    return {"kind": "opl", "header": header, "sections": sections}


def _structured_for(hub: ManufacturingKnowledgeHub, doc_type: str, document_id: str, tag: Optional[str], chunks: List[Any]) -> Optional[Dict[str, Any]]:
    store = hub.structured_store
    tag_u = (tag or "").upper()
    if doc_type == "DATASHEET":
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for tr in store.technical_records:
            if tr.document_id == document_id and (tr.equipment_tag or "").upper() == tag_u and _enum_value(tr.record_type) == "technical_parameter":
                groups.setdefault(tr.category or "Lainnya", []).append({"parameter": tr.parameter, "value": tr.value, "unit": tr.unit})
        return {"kind": "datasheet", "groups": [{"category": k, "rows": v} for k, v in groups.items()]} if groups else None
    if doc_type == "INTERLOCK":
        rels = [r for r in store.relationships if _enum_value(r.document_type) == "INTERLOCK" and (r.equipment_tag or "").upper() == tag_u]
        view = _interlock_view(rels, tag)
        return {"kind": "interlock", **view} if view["trips"] or view["permissives"] else None
    if doc_type == "PID":
        rows = []
        for tr in store.technical_records:
            # Structured records carry the P&ID's own register id, which can differ from the text chunk's id,
            # so match on document type and equipment instead.
            if _enum_value(tr.document_type) == "PID" and (tr.equipment_tag or "").upper() == tag_u and _enum_value(tr.record_type) == "setpoint":
                m = tr.metadata or {}
                rows.append({
                    "tag": m.get("instrument_tag"),
                    "instrument_type": m.get("instrument_type"),
                    "description": m.get("instrument_description"),
                    "setpoint": tr.value,
                    "unit": tr.unit,
                    "function": m.get("function"),
                })
        return {"kind": "pid", "rows": rows} if rows else None
    if doc_type == "MAINTENANCE":
        events = [m for m in store.maintenance_records if (m.equipment_tag or "").upper() == tag_u]
        if not events:
            return None
        events.sort(key=lambda m: str(m.date), reverse=True)
        return {"kind": "maintenance", "events": [{
            "event_id": m.event_id,
            "date": str(m.date),
            "failure_occurred": bool(m.failure_occurred),
            "failure_mode": m.failure_mode,
            "symptom": m.symptom,
            "root_cause": m.root_cause,
            "corrective_action": m.corrective_action,
            "downtime_hours": m.downtime_hours,
            "parts_replaced": list(m.parts_replaced or []),
        } for m in events]}
    if doc_type == "PLOT_PLAN":
        rows = [{"parameter": tr.parameter, "value": tr.value, "unit": tr.unit}
                for tr in store.technical_records
                if _enum_value(tr.document_type) == "PLOT_PLAN" and (tr.equipment_tag or "").upper() == tag_u and _enum_value(tr.record_type) == "coordinate"]
        return {"kind": "plot_plan", "rows": rows} if rows else None
    if doc_type == "OPL" and chunks:
        return _opl_sections("\n".join(c.content for c in chunks))
    return None


@router.get("/documents")
def list_documents(
    document_type: Optional[str] = Query(None),
    equipment_tag: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Case-insensitive match on title, document id, or tag"),
    hub: ManufacturingKnowledgeHub = Depends(_get_hub),
):
    registry = _load_json(_REGISTRY_PATH) or {}
    items = [_summarize(k, c, registry) for k, c in _group_documents(hub).items()]
    if document_type:
        items = [i for i in items if i["document_type"] == document_type.upper()]
    if equipment_tag:
        items = [i for i in items if i["equipment_tag"] == equipment_tag.upper()]
    if q:
        needle = q.lower()
        items = [
            i for i in items
            if needle in (i["title"] or "").lower()
            or needle in i["document_id"].lower()
            or needle in (i["equipment_tag"] or "").lower()
            or needle in (i["equipment_name"] or "").lower()
        ]
    items.sort(key=lambda i: (i["document_type"] or "", i["equipment_tag"] or "", i["document_id"]))
    return items


@router.get("/documents/{document_id}")
def get_document(
    document_id: str,
    equipment_tag: Optional[str] = Query(None),
    hub: ManufacturingKnowledgeHub = Depends(_get_hub),
):
    registry = _load_json(_REGISTRY_PATH) or {}
    wanted = (equipment_tag or "").upper()
    matches = [
        (k, c) for k, c in _group_documents(hub).items()
        if k[0].upper() == document_id.upper() and (not wanted or k[1] == wanted)
    ]
    if not matches:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found in repository.")
    if len(matches) > 1:
        raise HTTPException(
            status_code=409,
            detail=f"Document '{document_id}' exists for several equipment tags; pass equipment_tag.",
        )
    key, chunks = matches[0]
    detail = _summarize(key, chunks, registry)
    detail["structured"] = _structured_for(hub, detail["document_type"], detail["document_id"], detail["equipment_tag"], chunks)
    detail["chunks"] = [
        {
            "chunk_id": c.chunk_id,
            "title": c.title,
            "page": c.source.page,
            "sheet": c.source.sheet,
            "content": c.content,
        }
        for c in sorted(chunks, key=lambda c: (c.source.page or 0, c.chunk_id))
    ]
    return detail


@router.get("/plant")
def get_plant_tree(hub: ManufacturingKnowledgeHub = Depends(_get_hub)):
    """Plant -> Area -> Equipment tree, with document counts per equipment."""
    registry = _load_json(_REGISTRY_PATH) or {}
    hierarchy = _load_json(_HIERARCHY_PATH) or []
    area_desc = {
        n["tag"].replace("AREA-", ""): n["description"]
        for n in hierarchy if n.get("level") == "AREA"
    }

    doc_counts: Dict[str, int] = defaultdict(int)
    for (_doc_id, tag) in _group_documents(hub):
        doc_counts[tag] += 1

    maintenance_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"events": 0, "failures": 0})
    for m in hub.structured_store.maintenance_records:
        counts = maintenance_counts[(m.equipment_tag or "").upper()]
        counts["events"] += 1
        counts["failures"] += 1 if m.failure_occurred else 0

    areas: Dict[str, Dict[str, Any]] = {}
    for tag, e in registry.items():
        code = str(e.get("area", ""))
        # hierarchy.json keys areas by the 2-digit prefix (AREA-12 -> area 1200)
        desc = area_desc.get(code[:2]) or f"Area {code}"
        area = areas.setdefault(code, {"area": code, "name": desc, "equipment": []})
        area["equipment"].append({
            "tag": tag,
            "name": e.get("name"),
            "type": e.get("type"),
            "document_count": doc_counts.get(tag.upper(), 0),
            "maintenance_events": maintenance_counts[tag.upper()]["events"],
            "failure_count": maintenance_counts[tag.upper()]["failures"],
        })
    return {
        "plant": PLANT_NAME,
        "areas": sorted(areas.values(), key=lambda a: a["area"]),
    }


@router.get("/equipment/{equipment_tag}")
def get_equipment(equipment_tag: str, hub: ManufacturingKnowledgeHub = Depends(_get_hub)):
    """Equipment card: identity, protection logic (trips/permissives), instruments, actuators, components."""
    tag = equipment_tag.upper()
    registry = _load_json(_REGISTRY_PATH) or {}
    entry = registry.get(tag)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Equipment '{equipment_tag}' is not in the plant registry.")

    store = hub.structured_store
    rels = [r for r in store.relationships if (r.target_tag or "").upper() == tag]
    # The P&ID repeats trip/permissive links without effects; the interlock document is the authority for logic.
    interlock = _interlock_view([r for r in rels if _enum_value(r.document_type) == "INTERLOCK"], tag)

    instruments, seen_instruments = [], set()
    for r in rels:
        rtype = str(getattr(r.relationship, "value", r.relationship))
        if rtype in ("monitors", "controls") and r.source_tag not in seen_instruments:
            seen_instruments.add(r.source_tag)
            meta = r.metadata or {}
            instruments.append({
                "tag": r.source_tag,
                "role": rtype,
                "instrument_type": meta.get("instrument_type"),
                "description": r.context,
                "related_interlock": meta.get("related_interlock"),
            })

    hierarchy = _load_json(_HIERARCHY_PATH) or []
    components = [
        {"tag": n["tag"], "description": n["description"], "level": n["level"]}
        for n in hierarchy if n.get("parent_tag") == tag and n.get("level") in ("COMPONENT", "ACTUATOR")
    ]

    events = [m for m in store.maintenance_records if (m.equipment_tag or "").upper() == tag]
    failures = [m for m in events if m.failure_occurred]
    docs = [k for k in _group_documents(hub) if k[1] == tag]

    return {
        "tag": tag,
        "name": entry.get("name"),
        "type": entry.get("type"),
        "area": entry.get("area"),
        "symbol": _symbol_for(entry.get("type")),
        "has_diagram": bool(interlock["trips"] or interlock["permissives"] or instruments),
        "logic_tag": next(
            ((i["related_interlock"] or "").split()[0] for i in instruments if i.get("related_interlock")), None
        ),
        **interlock,
        "instruments": instruments,
        "components": components,
        "maintenance": {
            "events": len(events),
            "failures": len(failures),
            "last_date": max((str(m.date) for m in events), default=None),
        },
        "document_count": len(docs),
    }
