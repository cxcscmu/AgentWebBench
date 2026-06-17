import json
import math
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# Single source of truth for the results path (awbench/config.py).
sys.path.append(str(Path(__file__).resolve().parents[2]))
from awbench.config import RESULTS_DIR


def load_dataset(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_answer_field(answer: str) -> List[str]:
    """Parse the `answer` field from result_*.json into a list of doc_ids.

    Expected format (current): "[\"doc_id1\", \"doc_id2\"]" (JSON array as string).
    We first try json.loads; if it fails, fall back to a simple split.
    """
    if not answer:
        return []
    answer = answer.strip()
    try:
        parsed = json.loads(answer)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except Exception:
        print(f"Warning: Failed to parse answer: {answer}")

    # Fallback: comma / whitespace separated
    if answer.startswith("[") and answer.endswith("]"):
        answer = answer[1:-1]
    parts = [p.strip().strip('"\'') for p in answer.split(",") if p.strip()]
    return [p for p in parts if p]


def dcg_at_k(rels: List[int]) -> float:
    """Compute DCG given a list of binary relevances for ranks 1..k."""
    dcg = 0.0
    for i, rel in enumerate(rels):  # i: 0-based rank
        if rel > 0:
            dcg += rel / math.log2(i + 2)  # log2(rank+1)
    return dcg


def ndcg_and_recall_for_query(gt_docs: List[str], pred_docs: List[str], ks: Tuple[int, ...] = (1, 3, 5)) -> Tuple[Dict[int, float], Dict[int, float]]:
    gt_set = set(gt_docs)
    ndcg = {}
    recall = {}

    for k in ks:
        topk = pred_docs[:k]
        rels = [1 if d in gt_set else 0 for d in topk]

        # Recall@k
        if gt_docs:
            recall[k] = sum(rels) / len(gt_docs)
        else:
            recall[k] = 0.0

        # NDCG@k (binary relevance)
        dcg = dcg_at_k(rels)
        ideal_rels = [1] * min(len(gt_docs), k)
        idcg = dcg_at_k(ideal_rels)
        ndcg[k] = dcg / idcg if idcg > 0 else 0.0

    return ndcg, recall


def evaluate(results_dir: str, data_path: str, ks: Tuple[int, ...] = (1, 3, 5)) -> Dict[str, Dict[int, float]]:
    data = load_dataset(data_path)
    id2gt: Dict[str, List[str]] = {str(item["id"]): item.get("doc_ids", []) for item in data}

    results_path = Path(results_dir)
    result_files = sorted(results_path.glob("result_*.json"))
    if not result_files:
        print(f"No result_*.json found in {results_dir}")
        return {}

    # Accumulators
    ndcg_sum = {k: 0.0 for k in ks}
    recall_sum = {k: 0.0 for k in ks}
    count = 0

    per_query = {}

    for f in result_files:
        qid = f.stem.replace("result_", "")
        if qid not in id2gt:
            # Skip results not in dataset
            continue

        with open(f, "r", encoding="utf-8") as jf:
            res = json.load(jf)
        pred_answer = res.get("answer", "")
        pred_docs = parse_answer_field(pred_answer)
        gt_docs = id2gt[qid]

        if gt_docs is None:
            gt_docs = []

        nd, rc = ndcg_and_recall_for_query(gt_docs, pred_docs, ks=ks)

        per_query[qid] = {
            "gt_doc_ids": gt_docs,
            "pred_doc_ids": pred_docs,
            "ndcg": nd,
            "recall": rc,
        }

        for k in ks:
            ndcg_sum[k] += nd[k]
            recall_sum[k] += rc[k]
        count += 1

    if count == 0:
        print("No overlapping questions between results and data.")
        return {}

    metrics = {
        "NDCG": {k: ndcg_sum[k] / count for k in ks},
        "Recall": {k: recall_sum[k] / count for k in ks},
        "num_evaluated": count,
    }

    # Save metrics and per-query details
    out_metrics = results_path / "metrics_document.json"
    out_detail = results_path / "evaluation_results_per_query_document.json"
    with open(out_metrics, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    with open(out_detail, "w", encoding="utf-8") as f:
        json.dump(per_query, f, indent=2, ensure_ascii=False)

    # Result-dataset name mirrors the run scripts' convention: <task>_<filestem>
    # e.g. data/web_search/test_354.json -> web_search_test_354 ; data/web_recommendation/test_281.json -> web_recommendation_test_281
    _dp = Path(data_path)
    all_result_path = Path(RESULTS_DIR) / f"{_dp.parent.name}_{_dp.stem}"
    print(all_result_path / "evaluated_results.jsonl")
    with open(all_result_path / "evaluated_results.jsonl", "a", encoding="utf-8") as f:
        f.write(f"{results_path}: {json.dumps(metrics, ensure_ascii=False)}\n")

    print("Document retrieval evaluation (NDCG / Recall):")
    for k in ks:
        print(f"  NDCG@{k}:  {metrics['NDCG'][k]:.4f}")
        print(f"  Recall@{k}: {metrics['Recall'][k]:.4f}")

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Evaluate document retrieval results.")
    parser.add_argument("--results_dir", type=str, default="results/web_search_test_1/multi_agent_20251218", help="Results directory, e.g. results/web_search_test_1/multi_agent_20251218")
    parser.add_argument(
        "--data_path",
        type=str,
        default=None,
        help=(
            "Ground-truth data path. "
            "If not provided, will try to infer from results_dir."
        ),
    )
    args = parser.parse_args()

    args.results_dir = RESULTS_DIR + args.results_dir.split("results")[-1]

    # Auto-infer data_path if not explicitly given
    data_path = args.data_path
    if data_path is None:
        # Fallback: try run_config.json written by the retriever (if present)
        run_config = Path(args.results_dir.replace("results", "logs")) / "run_config.json"
        if run_config.exists():
            try:
                with open(run_config, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                data_path = cfg.get("batch_file")
            except Exception as e:
                print(f"Warning: Failed to load run_config.json: {e}")
                data_path = None

    evaluate(args.results_dir, data_path, ks=(1, 3, 5))


if __name__ == "__main__":
    main()
