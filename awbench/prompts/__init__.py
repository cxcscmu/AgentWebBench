"""
Prompt definitions for agents.
"""
# Question answer prompts
from awbench.prompts.qa import (
    qa_prompt_org,
    qa_prompt_prompt,
    qa_prompt_embed,
)

# Deep research prompts
from awbench.prompts.deep_research import (
    deep_research_prompt_org,
    deep_research_prompt_prompt,
    deep_research_prompt_embed,
)

# Shared components
from awbench.prompts.shared import (
    history_turns_base,
    format_reminder_prompt,
    summary_reminder_prompt,
)

# Content agent prompts
from awbench.prompts.content_agent import (
    content_agent_prompt_base,
)

# Web search prompts
from awbench.prompts.web_search import (
    web_search_prompt_org,
    web_search_prompt_prompt,
    web_search_prompt_embed,
)

# Recsys prompts
from awbench.prompts.web_recommendation import (
    web_recommendation_prompt_org,
    web_recommendation_prompt_prompt,
    web_recommendation_prompt_embed,
)

__all__ = [
    # Question answer
    'qa_prompt_org',
    'qa_prompt_prompt',
    'qa_prompt_embed',
    # Deep research
    'deep_research_prompt_org',
    'deep_research_prompt_prompt',
    'deep_research_prompt_embed',
    # Web search
    'web_search_prompt_org',
    'web_search_prompt_prompt',
    'web_search_prompt_embed',
    # Recsys
    'web_recommendation_prompt_org',
    'web_recommendation_prompt_prompt',
    'web_recommendation_prompt_embed',
    # Shared
    'format_reminder_prompt',
    'summary_reminder_prompt',
    # Content agent
    'content_agent_prompt_base',
]
