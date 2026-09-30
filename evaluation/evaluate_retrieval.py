import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import json
from typing import Dict, Any, List

from src.query.models import QueryRequest
from src.retrieval.retriever import HybridRetriever
from src.ingestion.document_loader import load_documents_from_dir


def evaluate_retrieval(
    questions_file: Path,
    extracted_dir: Path,
    k_values: List[int] = [1, 3, 5],
    report_output: Path = None
) -> Dict[str, Any]:
    with open(questions_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    registry = load_documents_from_dir(extracted_dir)
    retriever = HybridRetriever(registry)

    total_with_evidence = 0
    hits = {k: 0 for k in k_values}
    reciprocal_ranks = []
    sufficiency_correct = 0
    results_detail = []

    for item in questions:
        q_text = item["question"]
        ctx = item.get("session_context", {})
        expected_ev = set(item.get("expected_evidence", []))
        expected_suff = item.get("expected_sufficiency")

        req = QueryRequest(query=q_text, session_context=ctx)
        resp = retriever.query(req, top_k=max(k_values))

        # Check sufficiency prediction
        suff_status = str(resp.sufficiency.status.value if hasattr(resp.sufficiency.status, "value") else resp.sufficiency.status)
        is_suff_match = (suff_status == expected_suff)
        if is_suff_match:
            sufficiency_correct += 1

        retrieved_ids = [r.chunk_id for r in resp.results]
        item_hits = {}

        if expected_ev:
            total_with_evidence += 1
            # Compute Hit@K
            for k in k_values:
                top_k_ids = set(retrieved_ids[:k])
                hit = bool(expected_ev & top_k_ids)
                if hit:
                    hits[k] += 1
                item_hits[f"hit@{k}"] = hit

            # Compute Reciprocal Rank
            rr = 0.0
            for rank, cid in enumerate(retrieved_ids, start=1):
                if cid in expected_ev:
                    rr = 1.0 / rank
                    break
            reciprocal_ranks.append(rr)

        results_detail.append({
            "id": item["id"],
            "question": q_text,
            "intent": resp.understanding.intent,
            "equipment": resp.understanding.equipment_tag,
            "retrieved_top_3": retrieved_ids[:3],
            "hits": item_hits,
            "predicted_sufficiency": suff_status,
            "expected_sufficiency": expected_suff
        })

    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    suff_acc = (sufficiency_correct / len(questions)) * 100 if questions else 0.0

    metrics = {
        **{f"Hit@{k}": f"{(hits[k] / total_with_evidence) * 100:.1f}% ({hits[k]}/{total_with_evidence})" for k in k_values},
        "MRR": f"{mrr:.3f}",
        "Sufficiency Accuracy": f"{suff_acc:.1f}% ({sufficiency_correct}/{len(questions)})"
    }

    print("\n================ RETRIEVAL BENCHMARK EVALUATION ================")
    for k, score in metrics.items():
        print(f"  {k:<22}: {score}")
    print("================================================================\n")

    report_data = {
        "metrics": metrics,
        "details": results_detail
    }

    if report_output:
        report_output.parent.mkdir(parents=True, exist_ok=True)
        with open(report_output, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"Benchmark report saved to: {report_output}\n")

    return report_data


if __name__ == "__main__":
    q_path = BASE_DIR / "evaluation" / "retrieval_questions.json"
    ext_path = BASE_DIR / "data" / "extracted"
    out_path = BASE_DIR / "evaluation" / "benchmark_report.json"
    evaluate_retrieval(q_path, ext_path, report_output=out_path)
