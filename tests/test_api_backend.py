import pytest
import warnings
from fastapi.testclient import TestClient
from src.api.server import app

# Filter deprecation warning from starlette testclient
warnings.filterwarnings("ignore", category=DeprecationWarning)

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Chandra Asri" in data["service"]
    assert "GA-1201A" in data["active_equipment"]
    assert data["total_maintenance_records"] > 0


def test_api_readiness():
    response = client.get("/api/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["document_registry"] == "ready"
    assert data["vector_store"] == "ready"
    assert data["structured_store"] == "ready"
    assert data["failure_memory"] == "ready"
    assert data["plant_graph"] == "ready"
    assert data["total_documents"] > 0


def test_api_root_redirect():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (307, 302, 301)
    assert "/docs" in response.headers.get("location", "")


def test_api_query_datasheet():
    payload = {
        "query": "Berapa flow rate dan head dari pompa GA-1201A?",
        "equipment_tag": "GA-1201A"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["equipment_tag"] == "GA-1201A"
    assert data["confidence"] == "HIGH"
    assert len(data["citations"]) > 0
    assert data["confidence_breakdown"] is not None
    assert data["confidence_breakdown"]["asset_match_score"] >= 0.95
    assert data["query_id"] is not None
    assert data["trace"] is not None
    assert data["trace"]["total_latency_ms"] > 0.0


def test_api_query_ambiguous_refusal():
    payload = {
        "query": "What should I check if there is abnormal noise and vibration?",
        "equipment_tag": None
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["requires_clarification"] is True
    assert data["confidence"] in ("LOW", "UNVERIFIED")



def test_api_failure_memory_search():
    payload = {
        "query": "vibration high trip VSHH-1201",
        "equipment_tag": "GA-1201A"
    }
    response = client.post("/api/failure-memory/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["equipment_tag"] == "GA-1201A"
    assert data["has_historical_precedent"] is True
    assert len(data["similar_cases"]) > 0
    assert "Historical evidence != Current diagnosis" in data["disclaimer"]


def test_api_graph_hierarchy():
    response = client.get("/api/graph/hierarchy/GA-1201A")
    assert response.status_code == 200
    data = response.json()
    assert data["equipment_tag"] == "GA-1201A"
    assert "CAP-CILEGON" in data["hierarchy_path"]
    assert "AREA-12" in data["hierarchy_path"]
    assert "UNIT-1200" in data["hierarchy_path"]


def test_api_graph_protections():
    response = client.get("/api/graph/protections/GA-1201A")
    assert response.status_code == 200
    data = response.json()
    tags = [p["source_tag"] for p in data]
    assert "PSLL-1201" in tags
    assert "VSHH-1201" in tags


def test_api_graph_path_causality():
    payload = {
        "source_tag": "RO-1201",
        "target_tag": "MECH-SEAL-1201A",
        "max_depth": 4
    }
    response = client.post("/api/graph/path", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["hops"][0] == "RO-1201"
    assert data[0]["hops"][-1] == "MECH-SEAL-1201A"


def test_api_benchmark_report():
    response = client.get("/api/benchmark/report")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "Asset Resolution Accuracy" in data["metrics"]

