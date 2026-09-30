import json
from pathlib import Path
from typing import Tuple, List, Optional
from schemas.common import DocumentStatus
from src.retrieval.models import SufficiencyStatus
from src.generation.evidence import EvidencePackage, EvidenceItem
from src.generation.models import ConfidenceLevel, ConfidenceBreakdown

_CONF_PATH = Path(__file__).resolve().parent.parent.parent / "configs" / "confidence_config.json"
_DEFAULT_PENALTIES = {"conflicting_sources": 0.30, "obsolete_source": 0.50, "draft_source": 0.30}
_DEFAULT_THRESHOLDS = {"high_confidence_min": 0.75, "medium_confidence_min": 0.45}
if _CONF_PATH.exists():
    try:
        with open(_CONF_PATH, "r", encoding="utf-8") as _f:
            _data = json.load(_f)
            _DEFAULT_PENALTIES.update(_data.get("penalties", {}))
            _DEFAULT_THRESHOLDS.update(_data.get("thresholds", {}))
    except Exception:
        pass


class ConfidenceCalculator:
    """
    Step 23: Decomposed Confidence Calculator.
    Calculates auditable, mathematical confidence scores for manufacturing QA:
    Confidence = f(Asset, Source, Sufficiency, Coverage, Intent) - Penalties
    Configurable via configs/confidence_config.json.
    """

    @staticmethod
    def evaluate(package: EvidencePackage) -> Tuple[ConfidenceLevel, str, ConfidenceBreakdown]:
        items = package.items

        # 1. Asset Match Score (Weight: 25%)
        if package.sufficiency in (SufficiencyStatus.CLARIFICATION_REQUIRED, SufficiencyStatus.OUT_OF_SCOPE):
            asset_score = 0.0
        elif package.equipment_tag:

            tag_target = package.equipment_tag.upper()
            tag_matches = [
                it for it in items
                if it.equipment_tag and it.equipment_tag.upper() == tag_target
            ]
            if len(items) > 0:
                asset_score = len(tag_matches) / len(items)
                # Boost if target tag confirmed in top items
                if any(it.equipment_tag and it.equipment_tag.upper() == tag_target for it in items[:2]):
                    asset_score = max(asset_score, 0.95)
            else:
                asset_score = 0.0
        else:
            asset_score = 1.0  # General queries not bound to tag

        # 2. Source Validity Score (Weight: 25%)
        if not items:
            source_score = 0.0
        else:
            valid_count = 0
            for it in items:
                stat = str(it.source.status or "").lower()
                if any(v in stat for v in ["approved", "issued for operation", "issued for construction"]):
                    valid_count += 1
                elif "under review" in stat or "draft" in stat:
                    valid_count += 0.5
            source_score = valid_count / len(items)

        # 3. Retrieval Sufficiency Score (Weight: 25%)
        top_relevance = max([it.relevance_score for it in items], default=0.0)
        if package.sufficiency == SufficiencyStatus.SUFFICIENT:
            base_suff = 1.0
        elif package.sufficiency == SufficiencyStatus.CONFLICTING_EVIDENCE:
            base_suff = 0.4
        elif package.sufficiency == SufficiencyStatus.INSUFFICIENT:
            base_suff = 0.2
        else:  # MISMATCH or CLARIFICATION_NEEDED
            base_suff = 0.0

        suff_score = (0.6 * base_suff) + (0.4 * top_relevance)

        # 4. Coverage Score (Weight: 15%)
        covered_len = len(package.covered_knowledge_types)
        uncovered_len = len(package.uncovered_knowledge_types)
        total_types = covered_len + uncovered_len
        coverage_score = (covered_len / total_types) if total_types > 0 else (1.0 if items else 0.0)

        # 5. Intent Confidence (Weight: 10%)
        if package.intent and package.intent != "GENERAL_INFORMATION":
            intent_score = 1.0
        elif package.intent == "GENERAL_INFORMATION":
            intent_score = 0.85
        else:
            intent_score = 0.3

        # Penalties
        has_conflict = len(package.conflicts) > 0 or package.sufficiency == SufficiencyStatus.CONFLICTING_EVIDENCE
        conflict_penalty = _DEFAULT_PENALTIES.get("conflicting_sources", 0.30) if has_conflict else 0.0

        has_obsolete = any(
            str(it.source.status or "").lower() in ("obsolete", "superseded")
            for it in items
        )
        obsolete_penalty = _DEFAULT_PENALTIES.get("obsolete_source", 0.50) if has_obsolete else 0.0

        # Weighted calculation
        raw_score = (
            (0.25 * asset_score) +
            (0.25 * source_score) +
            (0.25 * suff_score) +
            (0.15 * coverage_score) +
            (0.10 * intent_score) -
            conflict_penalty -
            obsolete_penalty
        )
        final_score = round(max(0.0, min(1.0, raw_score)), 3)

        breakdown = ConfidenceBreakdown(
            asset_match_score=round(asset_score, 2),
            source_validity_score=round(source_score, 2),
            retrieval_sufficiency_score=round(suff_score, 2),
            coverage_score=round(coverage_score, 2),
            intent_confidence=round(intent_score, 2),
            conflict_penalty=round(conflict_penalty, 2),
            obsolete_penalty=round(obsolete_penalty, 2),
            raw_score=round(raw_score, 3),
            final_score=final_score
        )

        # Categorical rating and rationale dictated by Sufficiency Gate
        if package.sufficiency == SufficiencyStatus.INSUFFICIENT:
            level = ConfidenceLevel.UNVERIFIED
            final_score = min(final_score, 0.10)
            reason = "Evidence sufficiency gate failed. No approved documents match query criteria."
        elif package.sufficiency == SufficiencyStatus.OUT_OF_SCOPE:
            level = ConfidenceLevel.UNVERIFIED
            final_score = min(final_score, 0.10)
            reason = "Query domain does not match petrochemical equipment or plant documentation."
        elif package.sufficiency == SufficiencyStatus.CLARIFICATION_REQUIRED:
            level = ConfidenceLevel.LOW
            final_score = min(final_score, 0.25)
            reason = "Asset ambiguity prevents safe engineering response."
        elif package.sufficiency == SufficiencyStatus.CONFLICTING_EVIDENCE:
            level = ConfidenceLevel.LOW
            final_score = min(final_score, 0.35)
            reason = "Contradictory values detected between engineering documents. Manual verification required."
        elif final_score >= _DEFAULT_THRESHOLDS.get("high_confidence_min", 0.75) and not has_conflict:
            level = ConfidenceLevel.HIGH
            reason = (
                f"Direct evidence from approved engineering documents (Asset: {asset_score*100:.0f}%, "
                f"Source: {source_score*100:.0f}%, Sufficiency: {suff_score*100:.0f}%)."
            )
        elif final_score >= _DEFAULT_THRESHOLDS.get("medium_confidence_min", 0.45):
            level = ConfidenceLevel.MEDIUM
            reason = "Evidence is partially sufficient or from secondary operational documents."
        elif final_score >= 0.20:
            level = ConfidenceLevel.LOW
            reason = "Weak evidence grounding with low retrieval relevance or missing parameters."
        else:
            level = ConfidenceLevel.UNVERIFIED
            reason = "No verifiable evidence or asset mismatch prevented factual confidence."

        breakdown.final_score = final_score
        return level, reason, breakdown

