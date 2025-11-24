"""LLM-related exceptions."""


class LLMError(Exception):
    """Base error for LLM issues."""


class LLMResponseError(LLMError):
    """Raised when the LLM backend returns an unexpected response."""


class LLMNetworkError(LLMError):
    """Raised when HTTP/network issues occur while calling the LLM backend."""
