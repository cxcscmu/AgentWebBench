"""
Classic IR baseline for the Web Search task: API-based dense retrieval, no LLM / no agents.

For each query it calls the AgentWebBench search API and writes result_{id}.json files
compatible with the document evaluation (awbench/evaluation/document_evaluation.py).
This is the paper's "Classic IR" row -- a non-agent reference point.

Run from the repo root:
    python -m awbench.classic_ir --batch_file data/web_search/test_354.json --num_docs 10
"""
import os
import json
import argparse

from awbench.config import RESULTS_DIR
from awbench.data import load_questions
from awbench.utils.awbench_api import search as awbench_search


def retrieve_doc_ids(query_text, num_docs):
    """Top-k document IDs for a query from the AgentWebBench search API."""
    query_text = (query_text or "").strip()
    if not query_text:
        return []
    results = awbench_search(query_text, k=max(1, int(num_docs)))
    return [r["doc_id"] for r in results]


def write_result(answer_dir, qid, question, doc_ids):
    """Write one result_{id}.json in the format the document evaluation expects."""
    os.makedirs(answer_dir, exist_ok=True)
    result = {
        "model": "classic_ir",
        "question": question,
        # evaluation expects `answer` as a JSON array encoded as a string
        "answer": json.dumps(doc_ids, ensure_ascii=False),
        "turns": 0,
        "search count": 1 if doc_ids else 0,
        "script count": 0,
        "summary count": 0,
        "context lengths": [],
    }
    with open(os.path.join(answer_dir, f"result_{qid}.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Classic IR: API retrieval baseline (no LLM).")
    parser.add_argument("--batch_file", required=True,
                        help="Web Search dataset JSON (array of {id, question, doc_ids}).")
    parser.add_argument("--answer_dir", default=None,
                        help="Output dir; auto-derived under RESULTS_DIR/<dataset>/classic_ir if unset.")
    parser.add_argument("--num_docs", type=int, default=10,
                        help="Number of documents to retrieve per query (default: 10).")
    args = parser.parse_args()

    if args.answer_dir is None:
        dir_name = os.path.basename(os.path.dirname(os.path.abspath(args.batch_file)))
        file_name = os.path.splitext(os.path.basename(args.batch_file))[0]
        args.answer_dir = os.path.join(RESULTS_DIR, f"{dir_name}_{file_name}", "classic_ir")

    questions, ids = load_questions(args.batch_file)
    print(f"Loaded {len(questions)} questions from {args.batch_file}")
    print(f"Results -> {args.answer_dir}")

    os.makedirs(args.answer_dir, exist_ok=True)
    with open(os.path.join(args.answer_dir, "run_config.json"), "w", encoding="utf-8") as f:
        json.dump({
            "method": "classic_ir",
            "batch_file": os.path.abspath(args.batch_file),
            "answer_dir": os.path.abspath(args.answer_dir),
            "num_docs": int(args.num_docs),
        }, f, indent=2)

    for question, qid in zip(questions, ids):
        doc_ids = retrieve_doc_ids(question, args.num_docs)
        write_result(args.answer_dir, str(qid), question, doc_ids)
    print(f"Done. Results written to {args.answer_dir}")


if __name__ == "__main__":
    main()
