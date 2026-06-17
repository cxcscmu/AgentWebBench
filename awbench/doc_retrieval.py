"""
Document retrieval functions: query_docs using the AgentWebBench search API.
"""
from typing import Dict, List, Union
from awbench.utils.awbench_api import search as awbench_search


def query_docs(query: Union[Dict, str], num_docs: int = 10) -> List[dict]:
    """
    Args:
        query: {"query": query string} or a raw string query.
        num_docs: the number of documents to return

    Returns:
        A list of {"doc_id": ..., "doc_text": ...} dicts.
    """
    if isinstance(query, dict):
        query_text = query.get("query", "")
    elif isinstance(query, str):
        query_text = query
    else:
        raise ValueError("`query` must be either a dict or a JSON/raw string.")

    if not query_text:
        return []

    results = awbench_search(query_text, k=int(num_docs))
    return [{"doc_id": r["doc_id"], "doc_text": r["doc_text"]} for r in results]
