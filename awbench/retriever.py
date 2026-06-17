"""
WebsiteRetriever class for per-website document retrieval using the AgentWebBench API.
"""
from typing import List
from awbench.utils.awbench_api import search as awbench_search

_WEBSITE_RETRIEVERS: dict = {}


class WebsiteRetriever:
    """Per-website retriever backed by the AgentWebBench HTTP search API."""

    def __init__(self, website: str):
        self.website = website

    def search(self, query_text: str, num_docs: int) -> List[dict]:
        """Search top-k documents within this website via the search API."""
        if not query_text or num_docs <= 0:
            return []
        results = awbench_search(query_text, k=num_docs, website=self.website)
        return [{"doc_id": r["doc_id"], "doc_text": r["doc_text"]} for r in results]


def get_website_retriever(website: str, print_info: bool = True) -> WebsiteRetriever:
    """Get (or build) a WebsiteRetriever for a given website."""
    retriever = _WEBSITE_RETRIEVERS.get(website)
    if retriever is None:
        if print_info:
            print(f"Instantiate WebsiteRetriever: {website}")
        retriever = WebsiteRetriever(website)
        _WEBSITE_RETRIEVERS[website] = retriever
    return retriever
