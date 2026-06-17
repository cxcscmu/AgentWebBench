"""
HTTP client for the AgentWebBench ClueWeb22 search API.
"""
import json
import requests
from typing import List, Optional

# Default base URL; override via AWBENCH_API_BASE env var or awbench.config.AWBENCH_API_BASE
_DEFAULT_API_BASE = "https://www.clueweb22.us/awbench/search"


def _api_base() -> str:
    try:
        from awbench.config import AWBENCH_API_BASE
        return AWBENCH_API_BASE
    except Exception:
        return _DEFAULT_API_BASE


def search(query: str, k: int, website: Optional[str] = None) -> List[dict]:
    """
    Call the AgentWebBench search API.

    Args:
        query: search query text
        k: number of results to return
        website: optional domain filter (e.g. "en.wikipedia.org")

    Returns:
        List of {"doc_id": str, "doc_text": str, "url": str} dicts.
    """
    params: dict = {"query": query, "k": k}
    if website:
        params["website"] = website

    resp = requests.get(_api_base(), params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("results", []):
        doc_id = item.get("ClueWeb22-ID", "")
        clean_text_raw = item.get("Clean-Text", "")
        try:
            clean_text_obj = json.loads(clean_text_raw)
            doc_text = clean_text_obj.get("Clean-Text", clean_text_raw)
            doc_url = clean_text_obj.get("URL", "").strip()
        except (json.JSONDecodeError, TypeError):
            doc_text = clean_text_raw
            doc_url = ""
        results.append({"doc_id": doc_id, "doc_text": doc_text, "url": doc_url})

    return results
