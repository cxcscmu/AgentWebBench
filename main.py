"""
AgentWebBench entry point.

Parses CLI args, loads a task dataset, builds per-(task, method) prompts, and runs
the UserAgent over all remaining questions in parallel. The heavy lifting lives in
`awbench/` (agents, prompts, retrieval, data).
"""
import os
import json
import argparse
from datetime import datetime

from dotenv import load_dotenv

from awbench.agents.llm_client import API_TYPES
from awbench.agents.user_agent import UserAgent
from awbench.prompts.build import build_prompt
from awbench.data import (
    load_questions,
    load_web_recommendation,
    filter_completed_questions,
    web_recommendation_history_text,
)

load_dotenv("keys.env")


def parse_args():
    parser = argparse.ArgumentParser(description="Run AgentWebBench for one task.")
    parser.add_argument('--batch_file', type=str, help='Path to the task dataset JSON (array of samples)')
    parser.add_argument('--log_dir', type=str, default='logs', help='Log directory')
    parser.add_argument('--answer_dir', type=str, default='results', help='Result directory')
    parser.add_argument(
        '--task_type', type=str, default='qa',
        choices=['deep_research', 'qa', 'web_search', 'web_recommendation'],
        help='Task (paper names): deep_research, qa, web_search, web_recommendation. Default: qa.',
    )
    parser.add_argument('--api_type', type=str, default='gemini', choices=list(API_TYPES.keys()),
                        help='LLM API: gemini, gpt, hf, or local')
    parser.add_argument('--model_id', type=str, default=None, help='Model ID (default per API type if unset)')
    parser.add_argument('--url', type=str, default=None, help='Base URL for OpenAI-compatible APIs')
    parser.add_argument('--method', type=str, default='multi_agent',
                        help='Coordination method: classical, tool_embed, tool_prompt, multi_agent')
    parser.add_argument('--content_agent_max_turns', type=int, default=15, help='Max turns per content agent')
    parser.add_argument('--docs_per_site', type=int, default=3, help='Max documents per website for a content agent')
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.answer_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)

    user_agent_config = {
        "max_turns": 15,                  # max user-agent turns
        "num_docs": 3,                    # documents to retrieve per tool search
        "search_reminder_turn": 5,        # remind to stop searching / revise the report
        "final_answer_reminder_turn": 10, # remind to output the final report
        "final_answer_turn": 15,          # force the final answer
    }
    config_info = {
        "run_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "batch_file": args.batch_file,
        "task_type": args.task_type,
        "method": args.method,
        "api_type": args.api_type,
        "model_id": args.model_id,
        "url": args.url,
        "content_agent_max_turns": args.content_agent_max_turns,
        "docs_per_site": args.docs_per_site,
        "log_dir": args.log_dir,
        "answer_dir": args.answer_dir,
        # content and user agents share the same LLM config
        "llm_config": {"api_type": args.api_type, "model_id": args.model_id, "url": args.url},
        "user_agent_config": user_agent_config,
    }

    # Load dataset (web_recommendation keeps full sample dicts; others are (question, id) lists)
    if args.task_type == "web_recommendation":
        questions, ids = load_web_recommendation(args.batch_file)
    else:
        questions, ids = load_questions(args.batch_file)
    total_questions = len(questions)
    print(f"Loaded {total_questions} questions from {args.batch_file}")

    filtered, completed_count = filter_completed_questions(questions, ids, args.answer_dir)
    remaining_num = len(filtered)
    print('-----------------')
    print(f"Uncompleted questions: {list(filtered.keys())}")
    print('-----------------')
    print(f"Total dataset: {total_questions} | completed: {completed_count} | remaining: {remaining_num}")
    if remaining_num == 0:
        print("All questions have been completed!")
        return

    # Build per-question prompts
    prompts, remaining_questions, remaining_ids = [], [], []
    for qid, question in filtered.items():
        remaining_questions.append(question)
        remaining_ids.append(qid)
        text = web_recommendation_history_text(question) if args.task_type == "web_recommendation" else question
        prompts.append(build_prompt(args.task_type, args.method, text))

    config_info["dataset_info"] = {
        "total_questions": total_questions,
        "completed_questions": completed_count,
        "remaining_questions": remaining_num,
    }
    config_file = os.path.join(args.log_dir, "run_config.json")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_info, f, indent=2, ensure_ascii=False)
    print(f"Configuration saved to {config_file}")

    agent = UserAgent(
        user_agent_config,
        log_dir=args.log_dir,
        answer_dir=args.answer_dir,
        task_type=args.task_type,
        verbose=True,
        api_type=args.api_type,
        model_id=args.model_id,
        url=args.url,
        method=args.method,
        content_agent_max_turns=args.content_agent_max_turns,
        docs_per_site=args.docs_per_site,
    )
    print(f"Generating {args.task_type} mode...")
    agent.run_llm_loop_parallel(prompts, remaining_questions, remaining_ids)


if __name__ == '__main__':
    main()
