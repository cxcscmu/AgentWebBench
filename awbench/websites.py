"""
Website retrieval functions: query_websites and related utilities.
"""
import os
from typing import Dict, List, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from awbench.utils.awbench_api import search as awbench_search
from awbench.retriever import get_website_retriever


def _append_debug_log(log_dir: str, message: str) -> None:
    """Append a line to the per-run agent_debug.log, if a log dir is set."""
    if not log_dir:
        return
    with open(os.path.join(log_dir, "agent_debug.log"), 'a', encoding='utf-8') as f:
        f.write(message)


def retrieve_top_docs_for_websites(
    query_text: str,
    websites: List[str],
    num_docs: int,
) -> List[dict]:
    """
    Retrieve top docs per website using the AgentWebBench search API.
    """
    if not websites:
        return []

    results = []
    for website in websites:
        docs = get_website_retriever(website).search(query_text, num_docs)
        results.append({"website": website, "documents": docs})

    return results


def get_website_description(website: str) -> str:
    """Get website description."""
    from awbench.prompts.website_descriptions import WEBSITE_DESCRIPTIONS
    return WEBSITE_DESCRIPTIONS.get(website, "No description available")


def retrieve_top_docs_for_websites_with_agents(
    websites: List[str],
    num_docs: int,
    query_text: str = "",
    max_workers: int = 5,
    use_llm_agents: bool = True,
    log_dir: str = None,
    question_id: str = None,
    content_agent_max_turns: int = 5,
    llm_config: dict = None,
) -> List[dict]:
    """
    Retrieve top docs per website using separate LLM agents for each website.
    Each website is handled by an independent LLM agent for parallel processing.
    """
    results = []

    if not websites:
        return results

    _append_debug_log(log_dir, f"[DEBUG] Using LLM agents: use_llm_agents={use_llm_agents}, query_text={query_text}, websites={websites}\n")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_website = {
            executor.submit(
                retrieve_docs_for_single_website_with_llm_agent,
                website,
                query_text,
                num_docs,
                get_website_description(website),
                log_dir,
                question_id,
                content_agent_max_turns,
                llm_config,
            ): website
            for website in websites
        }

        for future in as_completed(future_to_website):
            result = future.result()
            results.append(result)

    return results


def retrieve_docs_for_single_website_with_llm_agent(
    website: str,
    query: str,
    num_docs: int,
    website_description: str = "No description available",
    log_dir: str = None,
    question_id: str = None,
    content_agent_max_turns: int = 5,
    llm_config: dict = None,
) -> str:
    """
    LLM agent function to retrieve docs for a single website.
    Each website is handled by a separate LLM agent.
    """
    from awbench.agents.content_agent import ContentAgent  # lazy import to avoid circular dependency

    _append_debug_log(log_dir, f"[DEBUG] Creating agent for {website}, query: {query[:50] if query else 'None'}...\n")

    agent = ContentAgent(website, website_description, log_dir=log_dir, question_id=question_id, llm_config=llm_config)

    _append_debug_log(log_dir, f"[DEBUG] Agent created for {website}, calling retrieve_documents\n")

    result = agent.retrieve_documents(query, num_docs, max_turns=content_agent_max_turns)

    _append_debug_log(log_dir, f"[DEBUG] Agent {website} completed, result length: {len(result) if result else 0}\n")

    return result


def query_websites(query: Union[Dict, str], agent_mode: bool = False, log_dir: str = None, question_id: str = None, content_agent_max_turns: int = 5, docs_per_site: int = 3, llm_config: dict = None) -> List[Union[str, dict]]:
    """
    Args:
        query: {"query": query string, "websites": [website names]} or a raw string query.
        agent_mode: whether to use agent-based retrieval.
        docs_per_site: number of documents to return for each website.
        log_dir: optional log directory for agent logging.

    Returns:
        On success, a list of per-website result dicts (e.g.
        {"website": ..., "documents": [...]}).  Error/edge cases
        instead return a list of plain status strings.
    """
    query_text = ""
    target_websites = None

    if isinstance(query, dict):
        print("Prompt mode")
        query_text = query.get("query", None)
        target_websites = query.get("websites", None)

        if target_websites is None or query_text is None:
            return ["No websites or query text provided."]

    elif isinstance(query, str):
        print("Global API mode")
        query_text = query

    if not query_text:
        return ["Not a valid query."]

    log_message = f"Search docs for [{query_text}] from {target_websites or 'global'}, {docs_per_site} docs each"
    print(log_message)

    if log_dir:
        debug_log = os.path.join(log_dir, "agent_debug.log")
        try:
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"{log_message}\n")
                f.flush()
        except Exception as e:
            print(f"Warning: Failed to write to debug log: {e}")

    if target_websites:
        # Per-website search
        if agent_mode:
            return retrieve_top_docs_for_websites_with_agents(
                target_websites, docs_per_site, query_text=query_text, use_llm_agents=True,
                log_dir=log_dir, question_id=question_id,
                content_agent_max_turns=content_agent_max_turns, llm_config=llm_config,
            )
        else:
            return retrieve_top_docs_for_websites(query_text, target_websites, docs_per_site)
    else:
        # Global search: no specific websites requested
        results = awbench_search(query_text, k=docs_per_site)
        docs = [{"doc_id": r["doc_id"], "doc_text": r["doc_text"]} for r in results]
        return [{"website": "global", "documents": docs}]
