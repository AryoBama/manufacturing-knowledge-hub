import sys
from pathlib import Path
import json
from typing import Dict, Any, List

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.query.models import QueryRequest
from src.retrieval.retriever import HybridRetriever
from src.ingestion.document_loader import load_documents_from_dir


def evaluate_adversarial_suite(
    adversarial_file: Path,
    extracted_dir: Path,
    report_output: Path = None
) -> Dict[str, Any]:
    """
    Executes the Adversarial Test Suite for the Industrial Manufacturing Knowledge Hub.
    Evaluates:
      1. Ghost Equipment Rejection Rate
      2. Cross-Asset Contamination Defense
      3. False Premise Refutation Readiness
      4. Safety Bypass Guardrail Activation
      5. Noisy Input / Slang Entity Resolution Rate
      6. Prompt Injection Resistance
      7. Overall Adversarial Robustness Score
    """
    with open(adversarial_file, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    registry = load_documents_from_dir(extracted_dir)
    retriever = HybridRetriever(registry)

    category_stats = {}
    total_cases = len(test_cases)
    passed_cases = 0
    results_detail = []

    for item in test_cases:
        cid = item["id"]
        category = item["category"]
        q_text = item["question"]
        ctx = item.get("session_context", {})
        expected_eq = item.get("expected_equipment")
        expected_suff = item.get("expected_sufficiency")
        expected_ev = set(item.get("expected_evidence", []))
        expected_behavior = item.get("expected_behavior")

        if category not in category_stats:
            category_stats[category] = {"total": 0, "passed": 0}
        category_stats[category]["total"] += 1

        req = QueryRequest(query=q_text, session_context=ctx)
        resp = retriever.query(req, top_k=5)

        # 1. Check Sufficiency status
        pred_suff = str(resp.sufficiency.status.value if hasattr(resp.sufficiency.status, "value") else resp.sufficiency.status)
        suff_passed = (pred_suff == expected_suff)

        # 2. Check Equipment Resolution
        pred_eq = resp.understanding.equipment_tag
        if expected_eq is None:
            eq_passed = (pred_eq is None) or resp.understanding.requires_clarification
        else:
            eq_passed = (pred_eq == expected_eq)

        # 3. Check Evidence Hit if expected
        retrieved_ids = [r.chunk_id for r in resp.results]
        ev_passed = True
        if expected_ev:
            ev_passed = bool(expected_ev & set(retrieved_ids[:3]))

        # Case overall pass criteria
        case_passed = suff_passed and eq_passed and ev_passed
        if case_passed:
            passed_cases += 1
            category_stats[category]["passed"] += 1

        results_detail.append({
            "id": cid,
            "category": category,
            "adversarial_type": item.get("adversarial_type"),
            "question": q_text,
            "expected_behavior": expected_behavior,
            "predicted_equipment": pred_eq,
            "expected_equipment": expected_eq,
            "predicted_sufficiency": pred_suff,
            "expected_sufficiency": expected_suff,
            "retrieved_top_3": retrieved_ids[:3],
            "passed": case_passed,
            "failure_reasons": [
                *(["Sufficiency mismatch"] if not suff_passed else []),
                *(["Equipment resolution mismatch"] if not eq_passed else []),
                *(["Missing expected refutation evidence"] if not ev_passed else [])
            ]
        })

    # Category performance breakdown
    category_breakdown = {}
    for cat, stats in category_stats.items():
        rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0.0
        category_breakdown[cat] = f"{rate:.1f}% ({stats['passed']}/{stats['total']})"

    overall_robustness = (passed_cases / total_cases) * 100 if total_cases > 0 else 0.0

    metrics = {
        "Overall Adversarial Robustness": f"{overall_robustness:.1f}% ({passed_cases}/{total_cases})",
        "Ghost Equipment Rejection": category_breakdown.get("ghost_equipment", "N/A"),
        "Cross-Asset Contamination Defense": category_breakdown.get("cross_asset_contamination", "N/A"),
        "False Technical Presupposition Defense": category_breakdown.get("false_technical_presupposition", "N/A"),
        "Safety Bypass Guardrail Activation": category_breakdown.get("safety_violation_bypass", "N/A"),
        "Severe Underspecification Handling": category_breakdown.get("severe_underspecification", "N/A"),
        "Noisy Entity Resolution": category_breakdown.get("noisy_entity_input", "N/A"),
        "Prompt Injection Resistance": category_breakdown.get("prompt_injection_ood", "N/A")
    }

    print("\n================ ADVERSARIAL BENCHMARK EVALUATION ================")
    for k, score in metrics.items():
        print(f"  {k:<42}: {score}")
    print("===================================================================\n")

    report_data = {
        "metrics": metrics,
        "category_summary": category_stats,
        "details": results_detail
    }

    if report_output:
        report_output.parent.mkdir(parents=True, exist_ok=True)
        with open(report_output, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"Adversarial report saved to: {report_output}\n")

    return report_data


if __name__ == "__main__":
    adv_file = BASE_DIR / "evaluation" / "adversarial_questions.json"
    ext_dir = BASE_DIR / "data" / "extracted"
    out_file = BASE_DIR / "evaluation" / "adversarial_report.json"
    evaluate_adversarial_suite(adv_file, ext_dir, report_output=out_file)
