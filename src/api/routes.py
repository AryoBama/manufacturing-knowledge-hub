import json
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from src.pipeline import ManufacturingKnowledgeHub
from src.generation.models import GeneratedAnswer
from schemas.maintenance import (
    FailureMemoryReport,
    FailurePatternSummary,
    HistoricalRCAInsight
)
from schemas.relationship import GraphPath
from src.api.models import (
    QueryApiRequest,
    FailureMemorySearchRequest,
    PathSearchRequest,
    HealthResponse,
    ReadinessResponse
)
from src.api.exceptions import (
    ManufacturingHubError,
    QueryValidationError,
    ResourceNotFoundError
)

logger = logging.getLogger("manufacturing_hub.api")
router = APIRouter(prefix="/api", tags=["Manufacturing Knowledge Hub"])

# Singleton pipeline accessor
_hub_instance: Optional[ManufacturingKnowledgeHub] = None


def get_hub() -> ManufacturingKnowledgeHub:
    global _hub_instance
    if _hub_instance is None:
        _hub_instance = ManufacturingKnowledgeHub()
    return _hub_instance


@router.get("/health", response_model=HealthResponse)
def health_check(hub: ManufacturingKnowledgeHub = Depends(get_hub)):
    """Liveness probe: verifies process is alive and returns active equipment dynamically."""
    return HealthResponse(
        status="ok",
        service="Chandra Asri Manufacturing Knowledge Hub API",
        version="1.0.0",
        total_maintenance_records=len(hub.failure_memory.records),
        total_relationships=len(hub.graph.records),
        active_equipment=hub.get_active_equipment()
    )


@router.get("/ready", response_model=ReadinessResponse)
def readiness_check(hub: ManufacturingKnowledgeHub = Depends(get_hub)):
    """Readiness probe: validates all subsystem dependencies before serving traffic."""
    try:
        total_docs = len(hub.registry.get_all()) if hub.registry else 0
        total_maint = len(hub.failure_memory.records) if hub.failure_memory else 0
        total_rels = len(hub.graph.records) if hub.graph else 0
        active_eq = hub.get_active_equipment()

        is_ready = bool(hub.registry and hub.vector_store and hub.structured_store)
        if not is_ready:
            raise HTTPException(status_code=503, detail="Knowledge Hub subsystems not fully initialized")

        return ReadinessResponse(
            status="ready",
            document_registry="ready",
            vector_store="ready",
            structured_store="ready",
            failure_memory="ready",
            plant_graph="ready",
            total_documents=total_docs,
            total_maintenance_records=total_maint,
            total_relationships=total_rels,
            active_equipment=active_eq
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Readiness probe check failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=503, detail="Service unavailable: subsystem initialization error")


@router.post("/query", response_model=GeneratedAnswer)
def execute_query(
    request: QueryApiRequest,
    hub: ManufacturingKnowledgeHub = Depends(get_hub)
):
    """
    Main technical Q&A endpoint.
    Executes hybrid retrieval, conflict resolution gate, and deterministic factual synthesis.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query text cannot be empty.")

    try:
        return hub.ask(
            question=request.query,
            session_context=request.session_context,
            explicit_tag=request.equipment_tag
        )
    except ManufacturingHubError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("Query execution failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal pipeline execution error. Check system logs.")


@router.post("/failure-memory/search", response_model=FailureMemoryReport)
def search_failure_memory(
    request: FailureMemorySearchRequest,
    hub: ManufacturingKnowledgeHub = Depends(get_hub)
):
    """
    Active failure memory search.
    Retrieves matching past incidents, recurring failure modes, and proven RCA mitigations.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Symptom query cannot be empty.")

    try:
        return hub.failure_memory.analyze_failure_memory(
            query=request.query,
            equipment_tag=request.equipment_tag
        )
    except ManufacturingHubError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("Failure memory search error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failure memory retrieval error. Check system logs.")


@router.get("/failure-memory/patterns/{equipment_tag}", response_model=FailurePatternSummary)
def get_failure_patterns(
    equipment_tag: str,
    hub: ManufacturingKnowledgeHub = Depends(get_hub)
):
    """Returns historical breakdown counts and top recurring failure modes for an equipment."""
    try:
        return hub.failure_memory.get_pattern_summary(equipment_tag=equipment_tag)
    except Exception as e:
        logger.error("Pattern summary error for %s: %s", equipment_tag, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve pattern summary.")


@router.get("/failure-memory/rca/{equipment_tag}", response_model=HistoricalRCAInsight)
def get_rca_insights(
    equipment_tag: str,
    symptom: Optional[str] = Query(None, description="Optional symptom filter"),
    hub: ManufacturingKnowledgeHub = Depends(get_hub)
):
    """Returns proven historical root causes and maintenance solutions."""
    try:
        return hub.failure_memory.get_rca_insights(equipment_tag=equipment_tag, symptom_keyword=symptom)
    except Exception as e:
        logger.error("RCA insights error for %s: %s", equipment_tag, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve RCA insights.")


@router.get("/graph/hierarchy/{equipment_tag}")
def get_plant_hierarchy(
    equipment_tag: str,
    hub: ManufacturingKnowledgeHub = Depends(get_hub)
):
    """Traverses plant hierarchy tree: Plant -> Area -> Unit -> Equipment."""
    try:
        return hub.graph.traverse_hierarchy(equipment_tag=equipment_tag)
    except Exception as e:
        logger.error("Hierarchy error for %s: %s", equipment_tag, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to traverse plant hierarchy.")


@router.get("/graph/protections/{equipment_tag}")
def get_protections(
    equipment_tag: str,
    hub: ManufacturingKnowledgeHub = Depends(get_hub)
):
    """Returns active SIS trip initiators, interlocks, and start permissives protecting equipment."""
    try:
        return hub.graph.get_protections(equipment_tag=equipment_tag)
    except Exception as e:
        logger.error("Protections error for %s: %s", equipment_tag, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve protections.")


@router.get("/graph/instruments/{equipment_tag}")
def get_instruments(
    equipment_tag: str,
    measure_type: Optional[str] = Query(None, description="Filter by measure, e.g. Pressure, Vibration, Temperature"),
    hub: ManufacturingKnowledgeHub = Depends(get_hub)
):
    """Returns measuring instruments monitoring equipment."""
    try:
        return hub.graph.get_instruments(equipment_tag=equipment_tag, measure_type=measure_type)
    except Exception as e:
        logger.error("Instruments error for %s: %s", equipment_tag, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve instruments.")


@router.get("/graph/components/{equipment_tag}")
def get_components(
    equipment_tag: str,
    hub: ManufacturingKnowledgeHub = Depends(get_hub)
):
    """Returns components part of the equipment."""
    try:
        return hub.graph.get_components(equipment_tag=equipment_tag)
    except Exception as e:
        logger.error("Components error for %s: %s", equipment_tag, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve components.")


@router.post("/graph/path", response_model=List[GraphPath])
def find_causal_path(
    request: PathSearchRequest,
    hub: ManufacturingKnowledgeHub = Depends(get_hub)
):
    """Finds directed multi-hop causal degradation or dependency paths via BFS."""
    try:
        return hub.graph.find_multi_hop_path(
            source_tag=request.source_tag,
            target_tag=request.target_tag,
            max_depth=request.max_depth
        )
    except Exception as e:
        logger.error("Pathfinding error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to execute graph path search.")


@router.get("/benchmark/report")
def get_benchmark_report(hub: ManufacturingKnowledgeHub = Depends(get_hub)):
    """
    Returns the latest automated baseline benchmark report via Hub service.
    """
    report = hub.get_latest_benchmark_report()
    if report.get("status") in ("pending", "error") and "metrics" not in report:
        raise HTTPException(status_code=404, detail="Benchmark report not found. Run evaluation first.")
    return report
