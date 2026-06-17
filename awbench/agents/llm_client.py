"""
Unified LLM API client for multiple providers (Gemini, GPT, HuggingFace Inference, Local).
"""
import os
import json
from typing import Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "keys.env"))

# API Type Configuration
API_TYPES = {
    "gemini": {
        "name": "gemini",
        "model_id": None,
        "api_key_env": "GOOGLE_API_KEY",
        "base_url": None
    },
    "gpt": {
        "name": "gpt",
        "model_id": None,
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
    },
    "hf": {
        "name": "hf",
        "model_id": None,
        "api_key_env": "HF_TOKEN",
        "base_url": "https://router.huggingface.co/v1",
    },
    "local": {
        "name": "local",
        "model_id": None,
        "api_key_env": "HF_TOKEN",
        "base_url": "http://localhost:8000/v1",
    },
}

MODEL_MAX_INPUT_TOKENS = {
    "deepseek-ai/DeepSeek-V3.2:novita": 128_000,        # Correct, https://api-docs.deepseek.com/quick_start/pricing, think v.s. non thing
    "gemini-3-flash-preview": 1_048_576,                # Correct, https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash
    "gpt-5-mini": 272_000,                              # Correct, through error message
    "Qwen/Qwen3-Next-80B-A3B-Thinking:hyperbolic": 262_144,  # Correct, https://qwen.ai/blog?id=4074cca80393150c248e508aa62983f9cb7d27cd&from=research.latest-advancements-list
    "Qwen/Qwen3-30B-A3B-Thinking-2507:nebius": 262_144,      # Correct, https://huggingface.co/Qwen/Qwen3-30B-A3B-Thinking-2507
    "Qwen/Qwen3-30B-A3B-Instruct-2507:nebius": 262_144,      # Correct, https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507
    "Qwen/Qwen3-30B-A3B-Thinking-2507": 262_144,            # Correct, https://huggingface.co/Qwen/Qwen3-30B-A3B-Thinking-2507
    "Qwen/Qwen3-30B-A3B-Instruct-2507": 262_144,            # Correct, https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507
    "Qwen/Qwen3-4B-Thinking-2507": 262_144,            # Correct, https://huggingface.co/Qwen/Qwen3-4B-Thinking-2507
    "Qwen/Qwen3-4B-Instruct-2507:nscale": 262_144,     # Correct, https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
    "Qwen/Qwen-14B": 2048,                             # Correct, https://huggingface.co/Qwen/Qwen-14B
    "Qwen/Qwen1.5-14B": 32_768,                        # Correct, https://huggingface.co/Qwen/Qwen1.5-14B
    "Qwen/Qwen2.5-14B": 131_072,                       # Correct, https://huggingface.co/Qwen/Qwen2.5-14B
    "Qwen/Qwen3-14B": 32_768,                          # Correct, 32,768 natively and 131,072 tokens with YaRN. --rope-scaling '{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}'
}

MAX_OUTPUT_TOKENS = 8192
LLM_REQUEST_TIMEOUT = 1800  # seconds
# Global client caches
_gemini_client = None
_openai_clients = {}  # Cache by (base_url, api_key) tuple


def get_gemini_client():
    """Return a cached Gemini client."""
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        api_key = os.getenv(API_TYPES["gemini"]["api_key_env"])
        if not api_key:
            raise ValueError(f"Missing {API_TYPES['gemini']['api_key_env']} environment variable")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def get_openai_client(base_url=None, api_key=None, extra_headers=None):
    """Return a cached OpenAI client."""
    # Use tuple as cache key (include extra_headers in key for HF)
    cache_key = (base_url, api_key, tuple(sorted(extra_headers.items())) if extra_headers else None)
    if cache_key not in _openai_clients:
        from openai import OpenAI
        _openai_clients[cache_key] = OpenAI(api_key=api_key, base_url=base_url, timeout=LLM_REQUEST_TIMEOUT, default_headers=extra_headers)
    return _openai_clients[cache_key]


def get_hf_client(base_url=None, api_key=None, org_name=None):
    """
    Return a cached HuggingFace Inference client (OpenAI-compatible).

    Args:
        base_url: Base URL for HuggingFace Inference API (default: https://router.huggingface.co/v1)
        api_key: HuggingFace token (default: from HF_TOKEN env var)
        org_name: Optional organization name for X-HF-Bill-To header

    Returns:
        OpenAI-compatible client configured for HuggingFace Inference
    """
    if api_key is None:
        api_key = os.getenv(API_TYPES["hf"]["api_key_env"])
        if not api_key:
            raise ValueError(f"Missing {API_TYPES['hf']['api_key_env']} environment variable")

    # Prepare extra headers for HF
    extra_headers = {}
    if org_name:
        extra_headers["X-HF-Bill-To"] = org_name

    # Delegate to get_openai_client, which owns the shared cache + construction logic.
    return get_openai_client(base_url=base_url, api_key=api_key, extra_headers=extra_headers or None)


def get_llm_client(api_type: str, model_id: str, url: Optional[str] = None, org_name: Optional[str] = None):
    """
    Get LLM client for the specified API type.

    Args:
        api_type: One of "gemini", "gpt", "hf", "local"
        model_id: Optional model ID (uses default for API type if not specified)
        url: Optional URL for GPT/OpenAI-compatible API
        org_name: Optional organization name for HuggingFace Inference (X-HF-Bill-To header)

    Returns:
        Tuple of (client, model_name)
    """
    if api_type not in API_TYPES:
        raise ValueError(f"Invalid api_type: {api_type}. Supported types: {list(API_TYPES.keys())}")

    api_config = API_TYPES[api_type]

    if url is None:
        url = api_config["base_url"]
    if not model_id:
        raise ValueError("model_id is required for LLM API")

    model_name = model_id

    if api_type == "gemini":
        client = get_gemini_client()
    elif api_type == "gpt":
        api_key = os.getenv(api_config["api_key_env"], "EMPTY")
        client = get_openai_client(base_url=url, api_key=api_key)
    elif api_type == "hf":
        # HuggingFace Inference API, https://huggingface.co/inference/models
        client = get_hf_client(base_url=url, org_name=org_name)
    elif api_type == "local":
        # Local OpenAI-compatible API (e.g., vLLM, SGLang)
        api_key = os.getenv(api_config["api_key_env"], "EMPTY")
        client = get_openai_client(base_url=url, api_key=api_key)
    else:
        raise ValueError(f"Unsupported API type: {api_type}")

    return client, model_name


def _truncate_doc_text(doc_text: str, scale_factor: float) -> str:
    """
    Truncate document text by removing middle content, keeping head and tail.
    Truncation is based on tokens, not characters.

    Args:
        doc_text: Original document text
        scale_factor: Scale factor (0.0 to 1.0) - how much to keep in tokens

    Returns:
        Truncated document text
    """
    from awbench.utils.token_calculator import tokenize_ids, detokenize

    if scale_factor >= 1.0:
        return doc_text
    if scale_factor <= 0.0:
        return ""

    # Encode once, then slice token ids directly (avoids re-tokenizing growing
    # substrings via binary search, which was O(log n) full tokenizations).
    token_ids = tokenize_ids(doc_text)
    total_tokens = len(token_ids)
    target_tokens = int(total_tokens * scale_factor)

    if target_tokens >= total_tokens:
        return doc_text

    truncation_marker = "...[truncated]..."
    marker_tokens = len(tokenize_ids(truncation_marker))
    available_tokens = target_tokens - marker_tokens
    if available_tokens <= 0:
        return ""

    head_target_tokens = available_tokens // 2
    tail_target_tokens = available_tokens - head_target_tokens

    head_text = detokenize(token_ids[:head_target_tokens]) if head_target_tokens > 0 else ""
    tail_text = detokenize(token_ids[total_tokens - tail_target_tokens:]) if tail_target_tokens > 0 else ""

    return head_text + truncation_marker + tail_text


def _truncate_information_content(content: str, scale_factor: float) -> str:
    """
    Truncate content within <information></information> tags.

    Args:
        content: Content between <information> tags (without the tags)
        scale_factor: Scale factor for truncation

    Returns:
        Truncated content
    """
    if 'doc_id' not in content or 'doc_text' not in content:
        return content

    if scale_factor >= 1.0:
        return content

    truncated_parts = []
    original_content = content

    # Preserve any unmatched <information> / </information> boundary so truncation
    # only touches the content between the last open tag and its close.
    extra_prefix = extra_suffix = ''
    last_open = original_content.rfind('<information>')
    if last_open != -1:
        extra_prefix = original_content[:last_open] + '<information>'
        content = original_content[last_open + len('<information>'):]

    first_close = content.find('</information>')
    if first_close != -1:
        extra_suffix = '</information>' + content[first_close + len('</information>'):]
        content = content[:first_close]

    try:
        content = json.loads(content)
    except Exception:
        raise ValueError(f"Invalid content: {content}")

    '''Format 1:
    [{"doc_id": "1", "doc_text": "doc_text_1"}, {"doc_id": "2", "doc_text": "doc_text_2"}]

    Format 2:
    [{"website": "www.google.com", "documents": [{"doc_id": "1", "doc_text": "doc_text_1"}, {"doc_id": "2", "doc_text": "doc_text_2"}]}]
    '''
    if not isinstance(content, list):
        return original_content

    for item in content:
        if not isinstance(item, dict):
            return original_content

        if item.get("website"):
            docs = item.get("documents", [])
            truncated_docs = []
            for doc in docs:
                truncated_doc = doc.copy()
                truncated_doc["doc_text"] = _truncate_doc_text(doc["doc_text"], scale_factor)
                truncated_docs.append(truncated_doc)
            item["documents"] = truncated_docs
        else:
            item["doc_text"] = _truncate_doc_text(item["doc_text"], scale_factor)
        truncated_parts.append(item)

    return extra_prefix + json.dumps(truncated_parts, indent=4) + extra_suffix


def _truncate_prompt_if_needed(prompt: str, model_name: str) -> str:
    """
    Truncate prompt if it exceeds model's max input tokens.

    Args:
        prompt: Input prompt
        model_name: Model name to get max tokens

    Returns:
        Truncated prompt if needed, original prompt otherwise
    """
    max_input_tokens = MODEL_MAX_INPUT_TOKENS.get(model_name)
    if max_input_tokens is None:
        raise ValueError(f"Model {model_name} not found in MODEL_MAX_INPUT_TOKENS")

    from awbench.utils.token_calculator import tokenize

    prompt_tokens = tokenize(prompt) # ~token size

    if prompt_tokens <= max_input_tokens:
        return prompt

    total_tokens_before = prompt_tokens

    blocks = prompt.split('<information>')[1:]

    if len(blocks) == 0:
        return prompt

    def remove_doc_text(item):
        if isinstance(item, dict):
            new_item = item.copy()
            if "doc_text" in new_item:
                new_item["doc_text"] = ""
            if "documents" in new_item:
                new_item["documents"] = [remove_doc_text(d) for d in new_item["documents"]]
            return new_item
        elif isinstance(item, list):
            return [remove_doc_text(i) for i in item]
        else:
            return item

    prompt_without_doc_text = prompt
    for block in blocks:
        block = block.split('</information>')[0]
        try:
            if 'doc_id' not in block or 'doc_text' not in block:
                continue
            block_json = json.loads(block)
            block_without_doc_text = remove_doc_text(block_json)
            block_str_without_doc_text = json.dumps(block_without_doc_text, indent=4)
            prompt_without_doc_text = prompt_without_doc_text.replace(
                f'<information>{block}</information>',
                f'<information>{block_str_without_doc_text}</information>',
                1
            )
        except Exception:
            continue

    tokens_without_doc_text = tokenize(prompt_without_doc_text)
    doc_tokens = total_tokens_before - tokens_without_doc_text
    fixed_tokens = tokens_without_doc_text + MAX_OUTPUT_TOKENS # add the response tokens
    remaining_budget = max_input_tokens - fixed_tokens

    if remaining_budget <= 0:
        scale_factor = 0.0
    else:
        scale_factor = remaining_budget / doc_tokens

    max_iterations = 5
    for iteration in range(max_iterations):
        truncated_prompt = prompt
        blocks = prompt.split('<information>')[1:]
        for block in blocks:
            block = block.split('</information>')[0]
            truncated_content = _truncate_information_content(block, scale_factor)
            truncated_prompt = truncated_prompt.replace(
                f'<information>{block}</information>',
                f'<information>{truncated_content}</information>',
                1
            )

        truncated_tokens = tokenize(truncated_prompt)

        if truncated_tokens + MAX_OUTPUT_TOKENS <= max_input_tokens:
            break

        excess_tokens = truncated_tokens + MAX_OUTPUT_TOKENS - max_input_tokens
        excess_ratio = excess_tokens / doc_tokens if doc_tokens > 0 else 1.0
        scale_factor = max(0.0, scale_factor - excess_ratio * 1.1)

    print(f"[Truncation] model={model_name}, max_input_token={max_input_tokens}, total={total_tokens_before}, "
          f"fixed={fixed_tokens}, docs={doc_tokens}, "
          f"budget={remaining_budget}, scale={scale_factor}, ",
          f"after truncation={tokenize(truncated_prompt)}")

    return truncated_prompt


def call_llm(
    api_type: str,
    client: Any,
    model_name: str,
    prompt: str,
    max_tokens: int = MAX_OUTPUT_TOKENS,
    **kwargs
) -> tuple[str, Optional[str]]:
    """
    Call LLM API and return response text and optional thought/reasoning.

    Args:
        api_type: One of "gemini", "gpt", "hf", "local"
        client: The API client instance
        model_name: Model name/ID to use
        prompt: Input prompt
        max_tokens: Maximum tokens to generate
        **kwargs: Additional API-specific parameters (e.g., extra_headers for HF)

    Returns:
        Tuple of (response_text, thought_text) where thought_text may be None
    """
    # Truncate prompt if needed before calling LLM
    actual_prompt = _truncate_prompt_if_needed(prompt, model_name)

    response_text = ""
    thought_text = ""

    if api_type == "gemini":
        from google.genai import types
        gemini_response = client.models.generate_content(
            model=model_name,
            contents=actual_prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(include_thoughts=True),
                max_output_tokens=max_tokens,
            ),
        )
        if gemini_response.candidates is None:
            print("Gemini response candidates is None")
            thought_text = ""
            response_text = ""
        else:
            for part in gemini_response.candidates[0].content.parts:
                if part.text:
                    if part.thought:
                        thought_text = part.text
                    else:
                        response_text = part.text
    elif api_type in ("gpt", "hf", "local"):
        if 'DeepSeek' in model_name:
            extra_body={
                "chat_template_kwargs": {'thinking': True}
            }
        else:
            extra_body = {}

        # GPT, HuggingFace Inference, and Local APIs all use OpenAI-compatible API
        gpt_response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": actual_prompt}],
            max_completion_tokens=max_tokens,
            extra_body=extra_body,
        )
        message = gpt_response.choices[0].message
        # Try to get reasoning content if available (for models like Qwen)
        response_text = message.content

        if hasattr(message, 'reasoning_content'):
            thought_text = message.reasoning_content
        else:
            thought_text = ""

    else:
        raise ValueError(f"Unsupported API type: {api_type}")

    return response_text, thought_text
