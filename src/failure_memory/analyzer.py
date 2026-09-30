import re
import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional, Set

from schemas.maintenance import (
    MaintenanceRecord,
    FailureModeFrequency,
    FailurePatternSummary,
    SimilarFailureCase,
    HistoricalRCAInsight,
    FailureMemoryReport,
)
from src.ingestion.metadata import resolve_equipment


# Standard mapping to canonical industrial failure modes when raw logs are Unspecified
FAILURE_MODE_KEYWORDS = [
    (r"\b(vibrat|vshh|getaran|shak)\b", "High Vibration / Dynamic Instability"),
    (r"\b(seal|bocor|leak|gland|menetes)\b", "Mechanical Seal Degradation / Leakage"),
    (r"\b(bearing|bantalan|spall|ti-1201|overheat|panas)\b", "Bearing Degradation / Overheating"),
    (r"\b(misalign|coupling|kopling|shaft|bengkok)\b", "Shaft / Coupling Misalignment"),
    (r"\b(grout|fondasi|foundation|baseplate|crack|retak)\b", "Baseplate / Foundation Deterioration"),
    (r"\b(overhaul|t/a|turnaround|wear ring|aus)\b", "Wear Ring / Overhaul Wear"),
    (r"\b(orifice|ro-1201|clog|tersumbat|plug)\b", "Flush Line / Orifice Blockage"),
]


def canonicalize_failure_mode(raw_mode: Optional[str], text_context: str) -> str:
    """Classifies a clean industrial failure mode name."""
    if raw_mode and raw_mode.strip().lower() not in ("unspecified", "none", "-", "", "yes", "true", "breakdown"):
        # If raw_mode is overly verbose (like full sentence), check regex keywords first
        if len(raw_mode.split()) > 6:
            for pattern, canonical_name in FAILURE_MODE_KEYWORDS:
                if re.search(pattern, raw_mode, re.IGNORECASE):
                    return canonical_name
        return raw_mode.strip()

    context = f"{raw_mode or ''} {text_context}".lower()
    for pattern, canonical_name in FAILURE_MODE_KEYWORDS:
        if re.search(pattern, context, re.IGNORECASE):
            return canonical_name

    return "Unscheduled Mechanical Anomaly"


def tokenize_text(text: str) -> Set[str]:
    """Tokenizes alphanumeric words ignoring trivial punctuation and common stop words."""
    words = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
    stop_words = {
        "and", "the", "with", "from", "for", "pada", "dan", "yang", "dari",
        "untuk", "dengan", "saat", "ini", "ada", "di", "ke", "atau", "pada",
        "was", "were", "been", "has", "had", "are", "per"
    }
    return {w for w in words if w not in stop_words}


def compute_symptom_similarity(query_tokens: Set[str], query_raw: str, record_text: str) -> float:
    """
    Computes a hybrid similarity score combining token Jaccard overlap
    and exact phrase/keyword bonuses.
    """
    if not query_tokens or not record_text.strip():
        return 0.0

    target_tokens = tokenize_text(record_text)
    if not target_tokens:
        return 0.0

    intersection = query_tokens.intersection(target_tokens)
    union = query_tokens.union(target_tokens)
    jaccard = len(intersection) / len(union) if union else 0.0

    # Overlap relative to query length (coverage)
    query_coverage = len(intersection) / len(query_tokens) if query_tokens else 0.0

    # Exact keyword bonus
    keyword_bonus = 0.0
    for q_tok in query_tokens:
        if len(q_tok) >= 4 and q_tok in record_text.lower():
            keyword_bonus += 0.05
    keyword_bonus = min(0.2, keyword_bonus)

    score = (0.4 * jaccard) + (0.4 * query_coverage) + keyword_bonus
    return min(1.0, max(0.0, score))


class FailureMemoryAnalyzer:
    """
    Active Failure Memory Engine.
    Processes historical CMMS / SAP PM maintenance records to:
    1. Identify recurring failure patterns and top failure modes
    2. Retrieve past similar incident cases matching reported symptoms
    3. Aggregate proven root causes and corrective actions
    4. Provide contextual safety guardrails ensuring:
       Historical evidence != Current diagnosis.
    """

    def __init__(self, records: Optional[List[MaintenanceRecord]] = None):
        self.records: List[MaintenanceRecord] = records or []
        self._by_tag = defaultdict(list)
        for r in self.records:
            tag = (r.equipment_tag or "").upper()
            if tag:
                self._by_tag[tag].append(r)

    @classmethod
    def from_processed_dir(cls, processed_dir: Path) -> "FailureMemoryAnalyzer":
        """Loads all maintenance records from data/processed directory."""
        records: List[MaintenanceRecord] = []
        if not processed_dir.exists():
            return cls([])

        for json_file in processed_dir.rglob("*.json"):
            if "maintenance" in json_file.name.lower():
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    for it in items:
                        if isinstance(it, dict) and "event_id" in it:
                            records.append(MaintenanceRecord.model_validate(it))
                except Exception as e:
                    print(f"[WARN] Error reading {json_file}: {e}")

        return cls(records=records)

    def get_pattern_summary(self, equipment_tag: str) -> FailurePatternSummary:
        """Computes statistical failure pattern summary for a specific equipment tag."""
        res = resolve_equipment(equipment_tag)
        norm_tag = res["equipment_tag"] if res.get("status") == "resolved" else equipment_tag.upper()

        eq_records = self._by_tag.get(norm_tag, [])
        total_records = len(eq_records)
        failure_records = [r for r in eq_records if r.failure_occurred]
        non_failure_count = total_records - len(failure_records)

        mode_counts = Counter()
        mode_samples = defaultdict(list)
        total_downtime = 0.0
        dates = []

        for r in failure_records:
            context = f"{r.symptom or ''} {r.root_cause or ''}"
            canon_mode = canonicalize_failure_mode(r.failure_mode, context)
            mode_counts[canon_mode] += 1
            mode_samples[canon_mode].append(r.event_id)
            total_downtime += float(r.downtime_hours or 0.0)
            if r.date:
                dates.append(str(r.date))

        total_failures = len(failure_records)
        top_modes: List[FailureModeFrequency] = []
        for mode, count in mode_counts.most_common(5):
            pct = (count / total_failures * 100.0) if total_failures > 0 else 0.0
            top_modes.append(
                FailureModeFrequency(
                    failure_mode=mode,
                    count=count,
                    percentage=round(pct, 1),
                    sample_event_ids=mode_samples[mode][:3]
                )
            )

        sorted_dates = sorted(dates) if dates else []
        earliest_date = sorted_dates[0] if sorted_dates else None
        latest_date = sorted_dates[-1] if sorted_dates else None

        return FailurePatternSummary(
            equipment_tag=norm_tag,
            total_maintenance_records=total_records,
            failure_count=total_failures,
            non_failure_count=non_failure_count,
            top_failure_modes=top_modes,
            total_downtime_hours=round(total_downtime, 2),
            earliest_record_date=earliest_date,
            latest_record_date=latest_date
        )

    def find_similar_cases(
        self,
        symptom_query: str,
        equipment_tag: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.15
    ) -> List[SimilarFailureCase]:
        """
        Retrieves historical failure records matching reported symptoms or problem statements.
        """
        query_tokens = tokenize_text(symptom_query)
        if not query_tokens:
            return []

        norm_tag = None
        if equipment_tag:
            res = resolve_equipment(equipment_tag)
            norm_tag = res["equipment_tag"] if res.get("status") == "resolved" else equipment_tag.upper()

        candidate_pool = self._by_tag.get(norm_tag, []) if norm_tag else self.records
        # Focus primarily on failure events or abnormal symptom reports
        failure_candidates = [r for r in candidate_pool if r.failure_occurred or r.symptom]

        scored_cases: List[SimilarFailureCase] = []
        for r in failure_candidates:
            combined_text = f"{r.symptom or ''} {r.failure_mode or ''} {r.root_cause or ''} {r.corrective_action or ''}"
            score = compute_symptom_similarity(query_tokens, symptom_query, combined_text)

            if score >= min_score:
                clean_mode = canonicalize_failure_mode(r.failure_mode, combined_text)
                scored_cases.append(
                    SimilarFailureCase(
                        event_id=r.event_id,
                        equipment_tag=r.equipment_tag,
                        date=str(r.date),
                        similarity_score=round(score, 3),
                        symptom=r.symptom,
                        failure_mode=clean_mode,
                        root_cause=r.root_cause,
                        corrective_action=r.corrective_action,
                        parts_replaced=r.parts_replaced,
                        source_file=r.source.file_name,
                        document_id=r.document_id
                    )
                )

        scored_cases.sort(key=lambda x: x.similarity_score, reverse=True)
        return scored_cases[:top_k]

    def get_rca_insights(
        self,
        equipment_tag: str,
        symptom_keyword: Optional[str] = None
    ) -> HistoricalRCAInsight:
        """
        Summarizes unique root causes, proven corrective actions, and parts replaced
        for equipment, optionally focused by symptom keyword.
        """
        res = resolve_equipment(equipment_tag)
        norm_tag = res["equipment_tag"] if res.get("status") == "resolved" else equipment_tag.upper()

        records = self._by_tag.get(norm_tag, [])
        root_causes = set()
        proven_actions = set()
        parts = set()
        work_orders = []

        kw_tokens = tokenize_text(symptom_keyword) if symptom_keyword else set()

        for r in records:
            if not r.failure_occurred:
                continue

            text_blob = f"{r.symptom or ''} {r.failure_mode or ''} {r.root_cause or ''}".lower()
            if kw_tokens:
                if not any(token in text_blob for token in kw_tokens):
                    continue

            if r.root_cause and r.root_cause.strip() not in ("-", "None", ""):
                root_causes.add(r.root_cause.strip())
            if r.corrective_action and r.corrective_action.strip() not in ("-", "None", ""):
                proven_actions.add(r.corrective_action.strip())
            for part in r.parts_replaced:
                if part and part.strip() not in ("-", "None", ""):
                    parts.add(part.strip())
            work_orders.append(r.event_id)

        return HistoricalRCAInsight(
            equipment_tag=norm_tag,
            root_causes=sorted(list(root_causes)),
            proven_actions=sorted(list(proven_actions)),
            replacement_parts_used=sorted(list(parts)),
            reference_work_orders=work_orders[:5]
        )

    def analyze_failure_memory(
        self,
        query: str,
        equipment_tag: Optional[str] = None
    ) -> FailureMemoryReport:
        """
        Generates an active failure memory analysis report.
        Strictly enforces the invariant: Historical evidence != Current diagnosis.
        """
        norm_tag = "GA-1201A"
        if equipment_tag:
            res = resolve_equipment(equipment_tag)
            norm_tag = res["equipment_tag"] if res.get("status") == "resolved" else equipment_tag.upper()

        patterns = self.get_pattern_summary(norm_tag)
        similar_cases = self.find_similar_cases(query, equipment_tag=norm_tag, top_k=5)
        rca_insights = self.get_rca_insights(norm_tag, symptom_keyword=query)

        has_precedent = len(similar_cases) > 0

        return FailureMemoryReport(
            equipment_tag=norm_tag,
            query_symptom=query,
            has_historical_precedent=has_precedent,
            pattern_summary=patterns,
            similar_cases=similar_cases,
            rca_insights=rca_insights,
            disclaimer=(
                "Historical evidence != Current diagnosis: Historical failure records indicate "
                "past occurrences, common root causes, and proven mitigations. They do not constitute "
                "an active real-time diagnosis for current plant conditions."
            )
        )
