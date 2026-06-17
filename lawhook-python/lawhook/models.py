# ─────────────────────────────────────────────────
#  Lawhook SDK — Response Models
#
#  Lightweight dataclasses — not Pydantic — so the
#  SDK doesn't force a Pydantic version on consumers.
#
#  Every model has a from_dict() classmethod that
#  builds it from the raw API JSON response.
#  Unknown/extra fields from the API are ignored
#  rather than raising — keeps the SDK forward
#  compatible with new API fields.
# ─────────────────────────────────────────────────

from dataclasses import dataclass, field
from datetime import datetime, date

def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO 8601 datetime strings, handling 'Z' suffix."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def _parse_date(value: str | None) -> date | None:
    """Parse ISO 8601 date strings."""
    if value is None:
        return None
    return date.fromisoformat(value)

# ──────────── API Keys ──────────────────────────────

@dataclass
class APIKey:
    """
    Represents an API key.
 
    Note: `key` (the full secret key) is only present
    in the response from create_key() — it is never
    returned again afterwards. Store it securely.
    """
    id: str
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    key: str | None = None  # Only set on creation response
    
    @classmethod
    def from_dict(cls, data: dict) -> "APIKey":
        return cls(
            id = data["id"],
            name = data["name"],
            key_prefix = data.get("key_prefix", ""),
            is_active = data.get("is_active", True),
            created_at = _parse_datetime(data.get("created_at")),
            last_used_at = _parse_datetime(data.get("last_used_at")),
            revoked_at = _parse_datetime(data.get("revoked_at")),
            key = data.get("key")  # Only on create response
        )
        
# ──────────── Subscriptions ─────────────────────────────
@dataclass
class Subscription:
    """
    Represents a webhook subscription to a
    jurisdiction + industry combination.
 
    Note: `signing_secret` is only present in the
    response from create() — it is never returned
    again afterwards. Use it to verify webhook
    signatures. Store it securely.
    """
    id: str
    name: str
    jurisdiction: str
    industry: str
    topics: list[str] | None
    webhook_url: str
    severity_min: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    signing_secret: str | None = None  # Only set on create response
    
    @classmethod
    def from_dict(cls, data: dict) -> "Subscription":
        return cls(
            id=data["id"],
            name=data["name"],
            jurisdiction=data["jurisdiction"],
            industry=data["industry"],
            topics=data.get("topics"),
            webhook_url=data["webhook_url"],
            severity_min=data["severity_min"],
            is_active=data.get("is_active", True),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            signing_secret=data.get("signing_secret"),
        )
        
# ──────────── Changes ──────────────────────────────

@dataclass
class ChangeDiff:
    """Structured diff of what changed in a regulatory update."""
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict | None) -> "ChangeDiff":
        if not data:
            return cls()
        return cls(
            added=data.get("added", []),
            removed=data.get("removed", []),
            modified=data.get("modified", []),
        )
        
@dataclass
class Change:
    """
    Represents a single detected regulatory change.
 
    `summary`, `severity`, and `diff` are populated by
    Lawhook's AI processing once status is "ready".
    """
    id:               str
    jurisdiction:     str
    industry:         str
    topic:            str | None
    source_authority: str
    source_url:       str
    summary:          str | None
    severity:         str | None       # "critical" | "major" | "minor"
    diff:             ChangeDiff
    status:           str              # "raw" | "processing" | "ready" | "failed"
    effective_date:   date | None
    detected_at:      datetime
    processed_at:     datetime | None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Change":
        return cls(
            id=data["id"],
            jurisdiction=data["jurisdiction"],
            industry=data["industry"],
            topic=data.get("topic"),
            source_authority=data["source_authority"],
            source_url=data["source_url"],
            summary=data.get("summary"),
            severity=data.get("severity"),
            diff=ChangeDiff.from_dict(data.get("diff")),
            status=data["status"],
            effective_date=_parse_date(data.get("effective_date")),
            detected_at=_parse_datetime(data.get("detected_at")),
            processed_at=_parse_datetime(data.get("processed_at")),
        )
        
@dataclass
class PaginatedChanges:
    """
    A page of Change results.
 
    Example:
        page = client.changes.list()
        for change in page.items:
            print(change.summary)
 
        if page.has_more:
            next_page = client.changes.list(page=page.page + 1)
    """
    items:    list[Change]
    total:    int
    page:     int
    limit:    int
    has_more: bool
    
    @classmethod
    def from_dict(cls, data: dict) -> "PaginatedChanges":
        return cls(
            items=[Change.from_dict(item) for item in data.get("items", [])],
            total=data.get("total", 0),
            page=data.get("page", 1),
            limit=data.get("limit", 20),
            has_more=data.get("has_more", False),
        )