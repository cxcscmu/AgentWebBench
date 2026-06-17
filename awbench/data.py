"""
Dataset loading for AgentWebBench.
"""
import os
import glob
import json


def load_questions(file_path):
    """Load a QA / web_search / deep_research dataset -> (questions, ids)."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [item["question"] for item in data], [item["id"] for item in data]


def load_web_recommendation(file_path):
    """Load a web_recommendation dataset -> (samples, ids).

    Merges pre-built user history (with titles) from the companion
    .user_history.jsonl file (same stem, same directory) into each sample.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    history_path = file_path.replace(".json", ".user_history.jsonl")
    if os.path.exists(history_path):
        history_by_id = {}
        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                history_by_id[item["id"]] = item["user_history"]
        for sample in data:
            sid = sample.get("id")
            if sid in history_by_id:
                sample["user_history"] = history_by_id[sid]

    return data, [item["id"] for item in data]


def filter_completed_questions(questions, ids, answer_dir, remove_uncompleted_log=True):
    """Drop questions that already have a result file; optionally clear stale logs."""
    filtered_questions_dict = {}
    completed_count = 0
    for i, question_id in enumerate(ids):
        answer_file = f"{answer_dir}/result_{question_id}.json"
        if os.path.exists(answer_file):
            completed_count += 1
        else:
            filtered_questions_dict[question_id] = questions[i]

    if remove_uncompleted_log:
        log_dir = answer_dir.replace("results", "logs")
        for question_id in filtered_questions_dict:
            for log_path in glob.glob(f"{log_dir}/content_agent_*_{question_id}_20*.log"):
                os.remove(log_path)
                print(f"Removed uncompleted content agent log: {log_path}")
            for log_path in glob.glob(f"{log_dir}/user_agent_*_{question_id}.*"):
                os.remove(log_path)
                print(f"Removed uncompleted user agent log: {log_path}")

    return filtered_questions_dict, completed_count


def web_recommendation_history_text(sample):
    """Chronological browsing-history string (doc_id/title/timestamp per line)."""
    history = sample.get("user_history", [])
    return "\n".join(
        json.dumps({"doc_id": h["doc_id"], "title": h.get("title", ""), "timestamp": h["timestamp"]})
        for h in history
    )
