"""Rough token-counting utilities backed by a lazily-loaded HuggingFace tokenizer.
"""

_MODEL_NAME = "Qwen/Qwen3-8B"
_tokenizer = None


def _get_tokenizer():
    """Load and cache the tokenizer on first use."""
    global _tokenizer
    if _tokenizer is None:
        from transformers import AutoTokenizer
        _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
    return _tokenizer


def tokenize_ids(text):
    """Return the list of token ids for ``text``."""
    return _get_tokenizer().encode(text)


def detokenize(ids):
    """Decode a list of token ids back into text."""
    return _get_tokenizer().decode(ids)


def tokenize(text):
    """Return the number of tokens in ``text``."""
    return len(tokenize_ids(text))


def main():
    print(tokenize("Hello, world!"))


if __name__ == "__main__":
    main()
