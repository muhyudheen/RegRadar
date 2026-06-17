# ─────────────────────────────────────────────────
#  Lawhook SDK — Exception Hierarchy
#
#  All SDK errors inherit from LawhookError so
#  developers can catch broadly or specifically:
#
#      try:
#          client.changes.list()
#      except LawhookError as e:
#          print(e)
#
#      try:
#          client.changes.get("bad_id")
#      except NotFoundError:
#          print("Change not found")
# ─────────────────────────────────────────────────

class LawhookError(Exception):
    """
    Base exception for all Lawhook SDK errors.
 
    Attributes:
        message:     human-readable error message
        status_code: HTTP status code, if applicable
        response:    raw response body (dict), if available
    """
    
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(message)
        
    def __str__(self) -> str:
        if self.status_code:
            return f"{self.status_code} Error: {self.message}"
        return self.message
    
class AuthenticationError(LawhookError):
    """
    Raised on HTTP 401.
 
    Indicates the API key is missing, invalid, or revoked.
    """
    pass

class NotFoundError(LawhookError):
    """
    Raised on HTTP 404.
 
    The requested resource (subscription, change) does not
    exist or does not belong to your API key.
    """    
    pass

class ValidationError(LawhookError): 
    """
    Raised on HTTP 422.
 
    Request data failed validation — check the `response`
    attribute for field-level details from the API.
    """
    pass

class RateLimitError(LawhookError):
    """
    Raised on HTTP 429.
 
    Attributes:
        retry_after: seconds to wait before retrying,
                     read from the Retry-After header.
                     None if the header was missing.
 
    Example:
        try:
            client.changes.list()
        except RateLimitError as e:
            time.sleep(e.retry_after or 60)
            client.changes.list()
    """
    
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict | None = None,
        retry_after: int | None = None,
    ):
        self.retry_after = retry_after
        super().__init__(message, status_code, response)
        
class ServerError(LawhookError):
    """
    Raised on HTTP 5xx.
 
    Indicates an error on Lawhook's side. Safe to retry
    with exponential backoff.
    """
    pass

class ConnectionError(LawhookError):
    """
    Raised when the request could not be sent at all —
    network failure, DNS failure, or timeout.
 
    Distinct from ServerError: the request never reached
    Lawhook's servers.
    """
    pass

def raise_for_status(status_code: int, body: dict | None) -> None:
    """
    Inspect an HTTP status code and raise the appropriate
    LawhookError subclass. Called internally by LawhookClient
    after every request — SDK users never call this directly.
 
    Does nothing if status_code indicates success (2xx).
    """
    if 200 <= status_code < 300:
        return
 
    detail = "Unknown error"
    if isinstance(body, dict):
        detail = body.get("detail", detail)
 
    if status_code == 401:
        raise AuthenticationError(
            detail or "Invalid or missing API key",
            status_code=status_code,
            response=body,
        )
 
    if status_code == 404:
        raise NotFoundError(
            detail or "Resource not found",
            status_code=status_code,
            response=body,
        )
 
    if status_code == 422:
        raise ValidationError(
            detail or "Validation failed",
            status_code=status_code,
            response=body,
        )
 
    if status_code == 429:
        # retry_after is attached separately by the client
        # since it comes from a response header, not the body
        raise RateLimitError(
            detail or "Rate limit exceeded",
            status_code=status_code,
            response=body,
        )
 
    if status_code >= 500:
        raise ServerError(
            detail or f"Lawhook server error ({status_code})",
            status_code=status_code,
            response=body,
        )
 
    # Catch-all for any other 4xx
    raise LawhookError(
        detail or f"Request failed ({status_code})",
        status_code=status_code,
        response=body,
    )