import json
from pathlib import Path
from collections import deque, defaultdict
from typing import List, Dict, Any, Optional, Set, Tuple

from schemas.relationship import (
    RelationshipType,
    RelationshipRecord,
    PlantHierarchyNode,
    GraphPath,
    GraphTraversalResult,
)
from src.ingestion.metadata import resolve_equipment


class PlantKnowledgeGraph:
    """
    Step 22: Industrial Plant Knowledge Graph Engine.
    Implements multi-hop graph querying, topological routing, safety interlock chains,
    and hierarchical plant navigation:
    Plant -> Area -> Unit -> Equipment -> Component -> Instrument -> Protection -> Failure Mode -> Action
    """

    def __init__(self):
        self.nodes: Dict[str, PlantHierarchyNode] = {}
        self.adj_out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.adj_in: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.records: List[RelationshipRecord] = []

    def add_node(
        self,
        tag: str,
        level: str,
        description: Optional[str] = None,
        parent_tag: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PlantHierarchyNode:
        """Registers a plant node in the knowledge graph."""
        tag_clean = tag.strip().upper()
        parent_clean = parent_tag.strip().upper() if parent_tag else None

        node = PlantHierarchyNode(
            tag=tag_clean,
            level=level.upper(),
            description=description,
            parent_tag=parent_clean,
            metadata=metadata or {}
        )
        self.nodes[tag_clean] = node

        # If parent is registered, automatically register hierarchical edges
        if parent_clean:
            edge_rel = RelationshipType.PART_OF if level.upper() in ("COMPONENT", "INSTRUMENT") else RelationshipType.LOCATED_IN
            self._add_edge(tag_clean, parent_clean, str(edge_rel), f"{level} hierarchy edge")

        return node

    def add_relationship(self, record: RelationshipRecord) -> None:
        """Adds a canonical RelationshipRecord to the graph."""
        self.records.append(record)
        src = record.source_tag.strip().upper()
        tgt = record.target_tag.strip().upper()

        # Ensure nodes exist
        if src not in self.nodes:
            self.add_node(tag=src, level="INSTRUMENT" if any(p in src for p in ["PT-", "PI-", "TI-", "FT-", "PSLL", "VSHH", "TSHH", "ZSO"]) else "EQUIPMENT")
        if tgt not in self.nodes:
            self.add_node(tag=tgt, level="EQUIPMENT")

        self._add_edge(
            source=src,
            target=tgt,
            predicate=str(record.relationship),
            context=record.context,
            record_id=record.relationship_id,
            document_id=record.document_id
        )

    def _add_edge(
        self,
        source: str,
        target: str,
        predicate: str,
        context: Optional[str] = None,
        record_id: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> None:
        """Internal helper to add directed edge in adjacency structures."""
        edge_data = {
            "source": source,
            "target": target,
            "relationship": predicate,
            "context": context,
            "record_id": record_id,
            "document_id": document_id
        }
        self.adj_out[source].append(edge_data)
        self.adj_in[target].append(edge_data)

    @classmethod
    def load_from_processed_dir(cls, processed_dir: Path) -> "PlantKnowledgeGraph":
        """Loads relationships from processed directory and seeds canonical hierarchy."""
        graph = cls()
        graph.seed_canonical_plant_hierarchy()

        if not processed_dir.exists():
            return graph

        for json_file in processed_dir.rglob("*.json"):
            if "relationship" in json_file.name.lower():
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    for it in items:
                        if isinstance(it, dict) and "relationship_id" in it:
                            graph.add_relationship(RelationshipRecord.model_validate(it))
                except Exception as e:
                    print(f"[WARN] Error reading {json_file}: {e}")

        return graph

    def load_from_knowledge_files(self, hierarchy_file: Path, relationships_file: Path) -> None:
        """Loads plant hierarchy nodes and relationships dynamically from external JSON knowledge store."""
        if hierarchy_file.exists():
            with open(hierarchy_file, "r", encoding="utf-8") as f:
                nodes_data = json.load(f)
            for item in nodes_data:
                self.add_node(
                    tag=item["tag"],
                    level=item["level"],
                    description=item.get("description"),
                    parent_tag=item.get("parent_tag"),
                    metadata=item.get("metadata")
                )

        if relationships_file.exists():
            with open(relationships_file, "r", encoding="utf-8") as f:
                rel_data = json.load(f)
            for item in rel_data:
                self._add_edge(
                    source=item["source"],
                    target=item["target"],
                    predicate=item["relationship"],
                    context=item.get("description", ""),
                    document_id=item.get("source_document")
                )

    def seed_canonical_plant_hierarchy(self, knowledge_dir: Optional[Path] = None) -> None:
        """
        Loads standard industrial plant hierarchy, topology, and causal links
        dynamically from data/knowledge store (with resilient fallback).
        """
        base_dir = knowledge_dir or Path(__file__).resolve().parent.parent.parent / "data" / "knowledge"
        hier_file = base_dir / "hierarchy.json"
        rel_file = base_dir / "relationships.json"
        if hier_file.exists() and rel_file.exists():
            self.load_from_knowledge_files(hier_file, rel_file)
            return

        # Resilient fallback if knowledge directory is unavailable
        self.add_node("CAP-CILEGON", "PLANT", "Chandra Asri Petrochemical Complex Cilegon")
        self.add_node("AREA-12", "AREA", "Polyethylene Hexane Feed & Purification Area", parent_tag="CAP-CILEGON")
        self.add_node("UNIT-1200", "UNIT", "Hexane Recovery and Pumping Unit", parent_tag="AREA-12")
        self.add_node("GA-1201A", "EQUIPMENT", "Hexane Feed Pump A (Operating)", parent_tag="UNIT-1200")
        self.add_node("GA-1201B", "EQUIPMENT", "Hexane Feed Pump B (Auto-Standby)", parent_tag="UNIT-1200")
        self.add_node("D-1201", "EQUIPMENT", "Hexane Storage / Feed Drum (Upstream Suction Vessel)", parent_tag="UNIT-1200")
        self.add_node("R-1201", "EQUIPMENT", "Gas-Phase Polyethylene Reactor (Downstream Destination)", parent_tag="UNIT-1200")
        self.add_node("MECH-SEAL-1201A", "COMPONENT", "John Crane Type 2100 Single Mechanical Seal Cartridge", parent_tag="GA-1201A")
        self.add_node("COUPLING-1201A", "COMPONENT", "Rexnord Flexible Disc Spacer Coupling", parent_tag="GA-1201A")
        self.add_node("RO-1201", "COMPONENT", "API Plan 11 Flush Restriction Orifice (Dia: 3.5 mm)", parent_tag="GA-1201A")
        self.add_node("PSLL-1201", "INSTRUMENT", "Suction Pressure Low-Low Trip Sensor (< 0.5 barg, 2oo3)", parent_tag="GA-1201A")
        self.add_node("VSHH-1201", "INSTRUMENT", "DE Bearing Vibration Switch High-High (> 7.1 mm/s RMS, 1oo2)", parent_tag="GA-1201A")
        self.add_node("TSHH-1201", "INSTRUMENT", "DE Bearing Temperature Switch High-High (> 85 C, 1oo2)", parent_tag="GA-1201A")
        self.add_node("FM-ORIFICE-PLUG", "FAILURE_MODE", "Restriction Orifice Blockage")
        self.add_node("FM-SEAL-DRYRUN", "FAILURE_MODE", "Mechanical Seal Face Dry Running")
        self.add_node("FM-SEAL-LEAK", "FAILURE_MODE", "Toxic Hexane Leakage via Seal Gland Drain")
        self.add_node("FM-MISALIGNMENT", "FAILURE_MODE", "Coupling Misalignment")
        self.add_node("FM-HIGH-VIBRATION", "FAILURE_MODE", "Excessive Vibration > 7.1 mm/s")
        self._add_edge("PSLL-1201", "GA-1201A", str(RelationshipType.TRIGGERS_TRIP), "Trip on low suction")
        self._add_edge("VSHH-1201", "GA-1201A", str(RelationshipType.TRIGGERS_TRIP), "Trip on high vibration")
        self._add_edge("RO-1201", "FM-ORIFICE-PLUG", str(RelationshipType.HAS_FAILURE_MODE), "Orifice blockage")
        self._add_edge("FM-ORIFICE-PLUG", "FM-SEAL-DRYRUN", str(RelationshipType.CAUSES), "Deprives flush")
        self._add_edge("FM-SEAL-DRYRUN", "FM-SEAL-LEAK", str(RelationshipType.CAUSES), "Heat checking")
        self._add_edge("FM-SEAL-LEAK", "MECH-SEAL-1201A", str(RelationshipType.PART_OF), "Seal damage")
        self._add_edge("COUPLING-1201A", "FM-MISALIGNMENT", str(RelationshipType.HAS_FAILURE_MODE), "Misalignment")
        self._add_edge("FM-MISALIGNMENT", "FM-HIGH-VIBRATION", str(RelationshipType.CAUSES), "Dynamic oscillation")
        self._add_edge("FM-HIGH-VIBRATION", "VSHH-1201", str(RelationshipType.MEASURES), "Sensor detects vibration")

    def get_protections(self, equipment_tag: str) -> List[Dict[str, Any]]:
        """Finds all protection instruments, trip initiators, and permissives protecting equipment."""
        res = resolve_equipment(equipment_tag)
        norm_tag = res["equipment_tag"] if res.get("status") == "resolved" else equipment_tag.upper()

        incoming = self.adj_in.get(norm_tag, [])
        protections = []
        seen = set()

        for edge in incoming:
            rel = edge["relationship"].lower()
            if rel in ("triggers_trip", "permissive_for", "permissive_start", "protects", "tripped_by"):
                key = (edge["source"], edge["relationship"])
                if key not in seen:
                    seen.add(key)
                    src_node = self.nodes.get(edge["source"])
                    protections.append({
                        "source_tag": edge["source"],
                        "relationship": edge["relationship"],
                        "context": edge["context"],
                        "description": src_node.description if src_node else None,
                        "document_id": edge.get("document_id")
                    })

        return protections

    def get_instruments(
        self,
        equipment_tag: str,
        measure_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Finds measuring and monitoring instruments associated with the equipment."""
        res = resolve_equipment(equipment_tag)
        norm_tag = res["equipment_tag"] if res.get("status") == "resolved" else equipment_tag.upper()

        instruments = []
        for tag, node in self.nodes.items():
            if node.level == "INSTRUMENT" and node.parent_tag == norm_tag:
                meas = (node.metadata.get("measures") or "").lower()
                if measure_type and measure_type.lower() not in meas and measure_type.lower() not in (node.description or "").lower():
                    continue
                instruments.append({
                    "tag": tag,
                    "description": node.description,
                    "measures": node.metadata.get("measures"),
                    "parent_tag": node.parent_tag
                })

        return instruments

    def get_components(self, equipment_tag: str) -> List[Dict[str, Any]]:
        """Finds components that are part of the target equipment."""
        res = resolve_equipment(equipment_tag)
        norm_tag = res["equipment_tag"] if res.get("status") == "resolved" else equipment_tag.upper()

        components = []
        for tag, node in self.nodes.items():
            if node.level == "COMPONENT" and node.parent_tag == norm_tag:
                components.append({
                    "tag": tag,
                    "description": node.description,
                    "level": node.level
                })
        return components

    def traverse_hierarchy(self, equipment_tag: str) -> Dict[str, Any]:
        """Traverses up the hierarchy tree to resolve full location context."""
        res = resolve_equipment(equipment_tag)
        norm_tag = res["equipment_tag"] if res.get("status") == "resolved" else equipment_tag.upper()

        current = self.nodes.get(norm_tag)
        if not current:
            return {"equipment_tag": norm_tag, "hierarchy_path": "", "levels": []}

        hierarchy_chain = [current]
        visited = {current.tag}

        while current and current.parent_tag:
            p_tag = current.parent_tag
            if p_tag in visited or p_tag not in self.nodes:
                break
            visited.add(p_tag)
            parent_node = self.nodes[p_tag]
            hierarchy_chain.append(parent_node)
            current = parent_node

        # Reverse so it flows from PLANT -> AREA -> UNIT -> EQUIPMENT
        chain = list(reversed(hierarchy_chain))
        return {
            "equipment_tag": norm_tag,
            "hierarchy_path": " -> ".join([n.tag for n in chain]),
            "levels": [{ "tag": n.tag, "level": n.level, "description": n.description } for n in chain]
        }

    def find_multi_hop_path(
        self,
        source_tag: str,
        target_tag: str,
        max_depth: int = 4
    ) -> List[GraphPath]:
        """
        Executes Breadth-First Search (BFS) to find directed multi-hop causal/topological paths
        between two plant entities.
        """
        src = source_tag.strip().upper()
        tgt = target_tag.strip().upper()

        if src not in self.nodes or tgt not in self.nodes:
            return []

        # Queue contains: (current_node, [nodes_visited], [edges_traversed], [contexts])
        queue = deque([(src, [src], [], [])])
        found_paths: List[GraphPath] = []

        while queue:
            curr_node, node_path, rel_path, ctx_path = queue.popleft()

            if curr_node == tgt and len(node_path) > 1:
                found_paths.append(
                    GraphPath(
                        hops=node_path,
                        relationships=rel_path,
                        contexts=ctx_path,
                        total_hops=len(rel_path)
                    )
                )
                if len(found_paths) >= 5:
                    break
                continue

            if len(rel_path) >= max_depth:
                continue

            for edge in self.adj_out.get(curr_node, []):
                next_node = edge["target"]
                if next_node not in node_path:  # Prevent cycles
                    queue.append((
                        next_node,
                        node_path + [next_node],
                        rel_path + [edge["relationship"]],
                        ctx_path + [edge.get("context")]
                    ))

        return found_paths

    def query_graph(
        self,
        equipment_tag: str,
        query_type: str = "ALL"
    ) -> GraphTraversalResult:
        """General interface for graph querying."""
        res = resolve_equipment(equipment_tag)
        norm_tag = res["equipment_tag"] if res.get("status") == "resolved" else equipment_tag.upper()

        related = set()
        for edge in self.adj_out.get(norm_tag, []):
            related.add(edge["target"])
        for edge in self.adj_in.get(norm_tag, []):
            related.add(edge["source"])

        return GraphTraversalResult(
            source_node=norm_tag,
            related_nodes=sorted(list(related)),
            metadata={
                "total_outgoing": len(self.adj_out.get(norm_tag, [])),
                "total_incoming": len(self.adj_in.get(norm_tag, [])),
            }
        )
