import time
import json
import uuid
import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from src.generation.models import QueryTraceLatency


class QueryTraceRecord(BaseModel):
    """Full execution trace for observability, auditability, and latency tracking."""
    query_id: str
    timestamp: str
    query_text: str
    equipment_tag: Optional[str] = None
    intent: Optional[str] = None
    sufficiency_status: Optional[str] = None
    confidence_level: Optional[str] = None
    confidence_score: float = 0.0
    citations_count: int = 0
    recommendations_count: int = 0
    latencies: QueryTraceLatency


class QueryTracer:
    """
    Step 24: Enterprise Query Tracer.
    Tracks latency per pipeline stage with microsecond precision and logs audit trail.
    """
    _counter: int = 100

    def __init__(self, query_text: str, query_id: Optional[str] = None):
        self.query_text = query_text
        if query_id:
            self.query_id = query_id
        else:
            QueryTracer._counter += 1
            now_str = datetime.datetime.now().strftime("%y%m%d")
            self.query_id = f"Q-{now_str}-{QueryTracer._counter:04d}"

        self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._stage_starts: Dict[str, float] = {}
        self._stage_latencies: Dict[str, float] = {
            "nlu": 0.0,
            "retrieval": 0.0,
            "sufficiency": 0.0,
            "generation": 0.0
        }

    def start_stage(self, stage: str) -> None:
        """Starts timing a pipeline stage ('nlu', 'retrieval', 'sufficiency', 'generation')."""
        self._stage_starts[stage.lower()] = time.perf_counter()

    def end_stage(self, stage: str) -> float:
        """Ends timing for a stage and accumulates latency in ms."""
        st = stage.lower()
        if st in self._stage_starts:
            duration = (time.perf_counter() - self._stage_starts[st]) * 1000.0
            self._stage_latencies[st] = round(duration, 2)
            return self._stage_latencies[st]
        return 0.0

    def finalize(self) -> QueryTraceLatency:
        """Computes total pipeline latency and constructs QueryTraceLatency."""
        total_ms = (time.perf_counter() - self._start_time) * 1000.0
        return QueryTraceLatency(
            query_id=self.query_id,
            timestamp=self.timestamp,
            nlu_latency_ms=self._stage_latencies.get("nlu", 0.0),
            retrieval_latency_ms=self._stage_latencies.get("retrieval", 0.0),
            sufficiency_latency_ms=self._stage_latencies.get("sufficiency", 0.0),
            generation_latency_ms=self._stage_latencies.get("generation", 0.0),
            total_latency_ms=round(total_ms, 2)
        )

    def log_audit(
        self,
        record: QueryTraceRecord,
        log_dir: Path = Path("logs")
    ) -> Path:
        """Appends audit trace entry to logs/audit_trail.jsonl."""
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "audit_trail.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.model_dump(), default=str) + "\n")
        return log_file
