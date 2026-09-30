import pytest
from pathlib import Path
from src.graph.engine import PlantKnowledgeGraph
from schemas.relationship import RelationshipType, GraphPath


@pytest.fixture
def graph():
    processed_dir = Path("data/processed/GA-1201A")
    return PlantKnowledgeGraph.load_from_processed_dir(processed_dir)


def test_plant_hierarchy_traversal(graph):
    res = graph.traverse_hierarchy("GA-1201A")
    assert res["equipment_tag"] == "GA-1201A"
    assert "CAP-CILEGON" in res["hierarchy_path"]
    assert "AREA-12" in res["hierarchy_path"]
    assert "UNIT-1200" in res["hierarchy_path"]
    assert "GA-1201A" in res["hierarchy_path"]
    assert res["levels"][0]["level"] == "PLANT"
    assert res["levels"][-1]["level"] == "EQUIPMENT"


def test_get_protections(graph):
    protections = graph.get_protections("GA-1201A")
    assert len(protections) >= 3
    source_tags = [p["source_tag"] for p in protections]
    assert "PSLL-1201" in source_tags
    assert "VSHH-1201" in source_tags
    assert "TSHH-1201" in source_tags


def test_get_measuring_instruments(graph):
    # Pressure instruments
    pressure_instruments = graph.get_instruments("GA-1201A", measure_type="Pressure")
    tags = [inst["tag"] for inst in pressure_instruments]
    assert "PT-1201" in tags or "PSLL-1201" in tags or "PI-1201" in tags

    # Vibration instruments
    vib_instruments = graph.get_instruments("GA-1201A", measure_type="Vibration")
    vib_tags = [inst["tag"] for inst in vib_instruments]
    assert "VSHH-1201" in vib_tags


def test_get_components(graph):
    components = graph.get_components("GA-1201A")
    tags = [c["tag"] for c in components]
    assert "MECH-SEAL-1201A" in tags
    assert "COUPLING-1201A" in tags
    assert "RO-1201" in tags


def test_multi_hop_path_causality_orifice_to_seal(graph):
    paths = graph.find_multi_hop_path("RO-1201", "MECH-SEAL-1201A", max_depth=4)
    assert len(paths) > 0
    p = paths[0]
    assert isinstance(p, GraphPath)
    assert p.hops[0] == "RO-1201"
    assert p.hops[-1] == "MECH-SEAL-1201A"
    assert p.total_hops == 4
    assert "FM-ORIFICE-PLUG" in p.hops
    assert "FM-SEAL-DRYRUN" in p.hops
    assert "FM-SEAL-LEAK" in p.hops


def test_multi_hop_path_misalignment_to_vibration_switch(graph):
    paths = graph.find_multi_hop_path("COUPLING-1201A", "VSHH-1201", max_depth=4)
    assert len(paths) > 0
    p = paths[0]
    assert p.hops[0] == "COUPLING-1201A"
    assert p.hops[-1] == "VSHH-1201"
    assert "FM-MISALIGNMENT" in p.hops
    assert "FM-HIGH-VIBRATION" in p.hops


def test_knowledge_graph_missing_nodes(graph):
    """Verifies graph engine safely rejects non-existent or phantom nodes without crashing."""
    # 1. Non-existent source node
    paths_missing_src = graph.find_multi_hop_path("GHOST-TAG-001", "GA-1201A")
    assert paths_missing_src == []

    # 2. Non-existent target node
    paths_missing_tgt = graph.find_multi_hop_path("GA-1201A", "GHOST-TAG-999")
    assert paths_missing_tgt == []

    # 3. Non-existent hierarchy traversal
    res = graph.traverse_hierarchy("NON-EXISTENT-PUMP")
    assert res["equipment_tag"] == "NON-EXISTENT-PUMP"
    assert res["levels"] == []


def test_knowledge_graph_cycle_resistance(graph):
    """Verifies graph traversal does not enter an infinite loop when encountering circular dependencies."""
    # Create deliberate cycle: CYC-A -> CYC-B -> CYC-C -> CYC-A
    graph.add_node("CYC-A", level="EQUIPMENT", description="Cycle Node A")
    graph.add_node("CYC-B", level="EQUIPMENT", description="Cycle Node B")
    graph.add_node("CYC-C", level="EQUIPMENT", description="Cycle Node C")

    graph._add_edge("CYC-A", "CYC-B", "causes", "A triggers B")
    graph._add_edge("CYC-B", "CYC-C", "causes", "B triggers C")
    graph._add_edge("CYC-C", "CYC-A", "causes", "C loops to A")

    # Traverse across the cycle with max depth > cycle length
    paths = graph.find_multi_hop_path("CYC-A", "CYC-C", max_depth=6)
    assert len(paths) == 1
    assert paths[0].hops == ["CYC-A", "CYC-B", "CYC-C"]
    assert paths[0].total_hops == 2


def test_knowledge_graph_incorrect_causal_path_rejection(graph):
    """Verifies graph rejects invalid causal leaps between disconnected entities without fabricating edges."""
    # Reverse direction: VSHH-1201 does NOT cause COUPLING-1201A
    rev_paths = graph.find_multi_hop_path("VSHH-1201", "COUPLING-1201A", max_depth=4)
    assert rev_paths == []

    # Disconnected domain
    unrelated_paths = graph.find_multi_hop_path("RO-1201", "VSHH-1201", max_depth=3)
    assert unrelated_paths == []

