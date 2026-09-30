import json
import time
from pathlib import Path
from typing import Dict, Any, List

from src.ingestion.document_loader import load_documents_from_dir
from src.retrieval.retriever import HybridRetriever
from src.query.routing import understand_query
from src.query.models import QueryRequest
from src.retrieval.sufficiency import evaluate_evidence_sufficiency
from src.retrieval.models import SufficiencyStatus
from src.vector import SQLiteVectorStore, TfidfDenseEmbedder, VectorIndexer


def run_retrieval_experiment():
    base_dir = Path(__file__).resolve().parent.parent
    extracted_dir = base_dir / "data" / "extracted"
    questions_file = base_dir / "evaluation" / "retrieval_questions.json"

    with open(questions_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    # 1. Setup Baseline Retriever (No Vector DB)
    reg = load_documents_from_dir(extracted_dir)
    baseline_retriever = HybridRetriever(registry=reg, vector_store=None)

    # 2. Setup Enhanced Retriever (With Vector DB)
    v_store = SQLiteVectorStore(":memory:")
    embedder = TfidfDenseEmbedder(dimension=384)
    indexer = VectorIndexer(vector_store=v_store, embedder=embedder)
    indexer.index(reg.get_all())

    enhanced_retriever = HybridRetriever(
        registry=reg,
        vector_store=v_store,
        embedder=embedder,
        lexical_weight=0.40,
        fuzzy_weight=0.20,
        vector_weight=0.40
    )

    def evaluate_engine(engine: HybridRetriever, name: str) -> Dict[str, Any]:
        total = 0
        hit1 = 0
        hit3 = 0
        hit5 = 0
        rr_sum = 0.0
        wrong_equipment = 0
        suff_correct = 0
        total_time = 0.0

        for q in questions:
            qid = q["id"]
            q_text = q["question"]
            exp_ev = q.get("expected_evidence", [])
            exp_eq = q.get("expected_equipment")
            exp_suff = q.get("expected_sufficiency")

            req = QueryRequest(query=q_text, session_context=q.get("session_context", {}))
            und = understand_query(req)

            start = time.perf_counter()
            results = engine.retrieve(und, top_k=5)
            elapsed = time.perf_counter() - start
            total_time += elapsed

            suff = evaluate_evidence_sufficiency(und, results)
            if suff.status.value == exp_suff:
                suff_correct += 1

            if not exp_ev:
                continue

            total += 1
            ret_ids = [r.chunk_id for r in results]

            # Check wrong equipment
            for r in results:
                if r.equipment_tag and exp_eq and r.equipment_tag.upper() != exp_eq.upper():
                    wrong_equipment += 1
                    break

            # Hits
            if any(ev in ret_ids[:1] for ev in exp_ev):
                hit1 += 1
            if any(ev in ret_ids[:3] for ev in exp_ev):
                hit3 += 1
            if any(ev in ret_ids[:5] for ev in exp_ev):
                hit5 += 1

            # MRR
            rank = None
            for idx, rid in enumerate(ret_ids, 1):
                if rid in exp_ev:
                    rank = idx
                    break
            if rank:
                rr_sum += 1.0 / rank

        avg_lat = (total_time / len(questions)) * 1000

        return {
            "Engine": name,
            "Questions Evaluated": len(questions),
            "Hit@1": f"{(hit1/total)*100:.1f}% ({hit1}/{total})" if total else "N/A",
            "Hit@3": f"{(hit3/total)*100:.1f}% ({hit3}/{total})" if total else "N/A",
            "Hit@5": f"{(hit5/total)*100:.1f}% ({hit5}/{total})" if total else "N/A",
            "MRR": f"{rr_sum/total:.3f}" if total else "N/A",
            "Sufficiency Accuracy": f"{(suff_correct/len(questions))*100:.1f}%",
            "Wrong Equipment Rate": f"{(wrong_equipment/total)*100:.1f}%" if total else "0.0%",
            "Mean Latency": f"{avg_lat:.2f} ms"
        }

    res_baseline = evaluate_engine(baseline_retriever, "Baseline (Metadata + Lexical + Subword)")
    res_enhanced = evaluate_engine(enhanced_retriever, "Enhanced (Metadata + Lexical + Subword + VectorDB)")

    print("\n" + "=" * 78)
    print(" CHANDRA ASRI PACIFIC - VECTOR DATABASE vs BASELINE RETRIEVAL EXPERIMENT")
    print("=" * 78)

    keys = ["Engine", "Hit@1", "Hit@3", "Hit@5", "MRR", "Sufficiency Accuracy", "Wrong Equipment Rate", "Mean Latency"]
    for k in keys:
        print(f" {k:<25} | {res_baseline[k]:<22} | {res_enhanced[k]}")
    print("=" * 78 + "\n")

    report_path = base_dir / "evaluation" / "vector_comparison_experiment.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"baseline": res_baseline, "enhanced": res_enhanced}, f, indent=2)

    print(f"Experiment results saved to: {report_path}\n")


if __name__ == "__main__":
    run_retrieval_experiment()
