# ─────────────────────────────────────────────────
#  Lawhook Python SDK
#
#  Usage:
#      from lawhook import LawhookClient
#
#      client = LawhookClient(api_key="lh_live_...")
#      changes = client.changes.list(jurisdiction="IN")
# ─────────────────────────────────────────────────
 
from lawhook.client import LawhookClient
from lawhook.exceptions import (
    AuthenticationError,
    ConnectionError,
    NotFoundError,
    RateLimitError,
    LawhookError,
    ServerError,
    ValidationError,
)
from lawhook.models import (
    APIKey,
    Change,
    ChangeDiff,
    PaginatedChanges,
    Subscription,
)
 
__version__ = "0.1.0"
 
__all__ = [
    "LawhookClient",
    # Exceptions
    "LawhookError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    "ConnectionError",
    # Models
    "APIKey",
    "Subscription",
    "Change",
    "ChangeDiff",
    "PaginatedChanges",
]
 