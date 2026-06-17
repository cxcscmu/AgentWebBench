"""
Build the user-agent prompt for a given (task_type, method).

Each task has three prompt variants and each coordination method maps to one of them:
  classical -> org,  tool_embed -> embed,  tool_prompt -> prompt,  multi_agent -> prompt
"""
from awbench.prompts.deep_research import deep_research_prompt_org, deep_research_prompt_prompt, deep_research_prompt_embed
from awbench.prompts.web_search import (
    web_search_prompt_org,
    web_search_prompt_prompt,
    web_search_prompt_embed,
)
from awbench.prompts.web_recommendation import web_recommendation_prompt_org, web_recommendation_prompt_prompt, web_recommendation_prompt_embed
from awbench.prompts.qa import (
    qa_prompt_org,
    qa_prompt_prompt,
    qa_prompt_embed,
)

# coordination method -> prompt variant
_METHOD_VARIANT = {
    "classical": "org",
    "tool_embed": "embed",
    "tool_prompt": "prompt",
    "multi_agent": "prompt",
}

# task_type -> {variant: template}
_TASK_TEMPLATES = {
    "deep_research": {"org": deep_research_prompt_org, "prompt": deep_research_prompt_prompt, "embed": deep_research_prompt_embed},
    "web_search": {
        "org": web_search_prompt_org,
        "prompt": web_search_prompt_prompt,
        "embed": web_search_prompt_embed,
    },
    "web_recommendation": {"org": web_recommendation_prompt_org, "prompt": web_recommendation_prompt_prompt, "embed": web_recommendation_prompt_embed},
    "qa": {
        "org": qa_prompt_org,
        "prompt": qa_prompt_prompt,
        "embed": qa_prompt_embed,
    },
}


def build_prompt(task_type: str, method: str, text: str) -> str:
    """Return the formatted user-agent prompt for (task_type, method).

    `text` is the question (qa / web_search / deep_research) or the browsing-history
    string (web_recommendation). Templates use either {question} or {query}; we pass
    both so the single placeholder in each template is filled.
    """
    if method not in _METHOD_VARIANT:
        raise ValueError(f"Unknown method {method!r}; expected one of {list(_METHOD_VARIANT)}")
    if task_type not in _TASK_TEMPLATES:
        raise ValueError(f"Unknown task_type {task_type!r}; expected one of {list(_TASK_TEMPLATES)}")
    template = _TASK_TEMPLATES[task_type][_METHOD_VARIANT[method]]
    return template.format(question=text, query=text)
