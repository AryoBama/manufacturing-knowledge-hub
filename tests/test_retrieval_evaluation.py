from pathlib import Path
from evaluation.evaluate_retrieval import evaluate_retrieval


def test_retrieval_benchmark_hit_rates():
    base_dir = Path(__file__).resolve().parent.parent
    q_path = base_dir / "evaluation" / "retrieval_questions.json"
    ext_path = base_dir / "data" / "extracted"

    result = evaluate_retrieval(q_path, ext_path)
    metrics = result["metrics"]

    # Assert Hit@1 >= 75%
    hit1_str = metrics["Hit@1"]
    hit1_val = float(hit1_str.split("%")[0])
    assert hit1_val >= 75.0, f"Hit@1 should be at least 75%, got {hit1_val}%"

    # Assert Hit@3 == 100%
    hit3_str = metrics["Hit@3"]
    hit3_val = float(hit3_str.split("%")[0])
    assert hit3_val == 100.0, f"Hit@3 should be 100%, got {hit3_val}%"

    # Assert Hit@5 == 100%
    hit5_str = metrics["Hit@5"]
    hit5_val = float(hit5_str.split("%")[0])
    assert hit5_val == 100.0, f"Hit@5 should be 100%, got {hit5_val}%"

    # Assert Sufficiency Accuracy is 100%
    suff_str = metrics["Sufficiency Accuracy"]
    suff_val = float(suff_str.split("%")[0])
    assert suff_val == 100.0, f"Sufficiency Accuracy should be 100%, got {suff_val}%"
