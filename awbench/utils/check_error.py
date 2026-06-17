import random

def is_fatal_error(error: Exception) -> bool:
    """
    Check if an error is fatal (non-recoverable) and should stop the entire task.
    
    Fatal errors include:
    - Token count exceeds maximum (400 INVALID_ARGUMENT)
    - Authentication errors (401, 403)
    - Invalid arguments (400, except rate limits)
    - Other 4xx errors (except 429 rate limit)
    
    Returns:
        True if the error is fatal and should stop the task, False otherwise
    """
    error_str = str(error)
    error_type = type(error).__name__
    error_lower = error_str.lower()

    # Check for token limit exceeded
    if "token count exceeds" in error_lower or "exceeds the maximum number of tokens" in error_lower:
        return True

    # Check for context length errors
    if "context" in error_lower and ("length" in error_lower or "exceed" in error_lower):
        return True

    # Check for authentication/authorization errors
    if "401" in error_str or "403" in error_str or "unauthorized" in error_lower or "forbidden" in error_lower:
        return True

    # Check for invalid argument errors (400) that are not rate limits
    if "400" in error_str and "invalid" in error_lower and "rate" not in error_lower:
        return True

    # Check for ClientError with 400 status
    if error_type == "ClientError":
        try:
            # Try to extract status code from error
            if hasattr(error, 'status_code') and error.status_code == 400:
                # Check if it's a token limit error
                if "token" in error_lower or "exceed" in error_lower:
                    return True
        except Exception:
            print(f"Warning: Failed to check status code: {error}")
    
    return False
