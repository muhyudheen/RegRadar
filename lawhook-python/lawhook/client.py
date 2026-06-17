# ─────────────────────────────────────────────────
#  Lawhook SDK — Client
#
#  Usage:
#      from lawhook import LawhookClient
#
#      client = LawhookClient(api_key="lh_live_...")
#
#      # Subscriptions
#      sub = client.subscriptions.create(
#          name="India Fintech Monitor",
#          jurisdiction="IN",
#          industry="fintech",
#          topics=["KYC", "AML"],
#          webhook_url="https://yourapp.com/webhooks",
#          severity_min="major",
#      )
#      print(sub.signing_secret)  # store this — shown once
#
#      # Changes
#      page = client.changes.list(jurisdiction="IN", industry="fintech")
#      for change in page.items:
#          print(change.severity, change.summary)
#
#      results = client.changes.search("KYC")
#
#  All methods raise LawhookError subclasses on failure —
#  see exceptions.py.
# ─────────────────────────────────────────────────

from __future__ import annotations

import httpx

from lawhook.exceptions import (
    ConnectionError,
    RateLimitError,
    raise_for_status,
)

from lawhook.models import (
    APIKey,
    Change,
    PaginatedChanges,
    Subscription,
)
 
DEFAULT_BASE_URL = "https://api.lawhook.dev"
DEFAULT_TIMEOUT  = 30.0
 
 
class LawhookClient:
    """
    Main entry point for the Lawhook SDK.
 
    Args:
        api_key:  Your Lawhook API key (starts with "lh_live_").
        base_url: Override the API base URL — useful for local
                  development (e.g. "http://127.0.0.1:8000").
        timeout:  Request timeout in seconds. Default 30s.
 
    The client is safe to reuse across requests — it holds
    a single underlying HTTP connection pool. Create one
    instance and reuse it throughout your application.
    """
 
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        if not api_key:
            raise ValueError("api_key is required")
 
        self._api_key  = api_key
        self._base_url = base_url.rstrip("/")
 
        self._http = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
                "User-Agent":    "lawhook-python/0.1.0",
            },
        )
 
        # Sub-resource namespaces
        self.subscriptions = _SubscriptionsAPI(self)
        self.changes       = _ChangesAPI(self)
        self.auth          = _AuthAPI(self)
 
    # ── Internal request helper ───────────────────
 
    def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict | None:
        """
        Make an HTTP request and return the parsed JSON body.
 
        Raises LawhookError subclasses on any non-2xx response.
        Raises ConnectionError if the request couldn't be sent.
 
        Returns None for 204 No Content responses.
        """
        try:
            response = self._http.request(
                method,
                path,
                json=json,
                params=params,
            )
        except httpx.TimeoutException as e:
            raise ConnectionError(f"Request timed out: {e}")
        except httpx.RequestError as e:
            raise ConnectionError(f"Request failed: {e}")
 
        # 204 No Content — nothing to parse
        if response.status_code == 204:
            return None
 
        # Try to parse JSON body — may be empty/invalid on errors
        try:
            body = response.json()
        except ValueError:
            body = None
 
        # Special handling for 429 — attach Retry-After header
        if response.status_code == 429:
            retry_after_header = response.headers.get("Retry-After")
            retry_after = (
                int(retry_after_header)
                if retry_after_header and retry_after_header.isdigit()
                else None
            )
            detail = "Rate limit exceeded"
            if isinstance(body, dict):
                detail = body.get("detail", detail)
 
            raise RateLimitError(
                detail,
                status_code=429,
                response=body,
                retry_after=retry_after,
            )
 
        raise_for_status(response.status_code, body)
 
        return body
 
    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()
 
    def __enter__(self) -> "LawhookClient":
        return self
 
    def __exit__(self, *args) -> None:
        self.close()
 
 
# ── Auth Sub-API ──────────────────────────────────
 
class _AuthAPI:
    """Accessed via client.auth"""
 
    def __init__(self, client: LawhookClient):
        self._client = client
 
    def create_key(self, name: str) -> APIKey:
        """
        Generate a new API key.
 
        The returned APIKey.key contains the full secret —
        it is shown only once and cannot be retrieved again.
        Store it securely immediately.
        """
        body = self._client._request(
            "POST", "/v1/auth/keys", json={"name": name}
        )
        return APIKey.from_dict(body)
 
    def list_keys(self) -> list[APIKey]:
        """List all API keys (secrets are not included)."""
        body = self._client._request("GET", "/v1/auth/keys")
        return [APIKey.from_dict(item) for item in body]
 
    def revoke_key(self, key_id: str) -> None:
        """Revoke (delete) an API key by ID."""
        self._client._request("DELETE", f"/v1/auth/keys/{key_id}")
 
 
# ── Subscriptions Sub-API ─────────────────────────
 
class _SubscriptionsAPI:
    """Accessed via client.subscriptions"""
 
    def __init__(self, client: LawhookClient):
        self._client = client
 
    def create(
        self,
        name: str,
        jurisdiction: str,
        industry: str,
        webhook_url: str,
        topics: list[str] | None = None,
        severity_min: str = "minor",
    ) -> Subscription:
        """
        Create a new webhook subscription.
 
        The returned Subscription.signing_secret is shown
        only once — store it securely to verify incoming
        webhook signatures.
 
        Raises ValidationError if webhook_url fails SSRF
        validation or other fields are invalid.
        """
        body = self._client._request(
            "POST",
            "/v1/subscriptions",
            json={
                "name": name,
                "jurisdiction": jurisdiction,
                "industry": industry,
                "topics": topics,
                "webhook_url": webhook_url,
                "severity_min": severity_min,
            },
        )
        return Subscription.from_dict(body)
 
    def list(self) -> list[Subscription]:
        """List all subscriptions for this API key."""
        body = self._client._request("GET", "/v1/subscriptions")
        return [Subscription.from_dict(item) for item in body]
 
    def get(self, subscription_id: str) -> Subscription:
        """
        Get a single subscription by ID.
 
        Raises NotFoundError if it doesn't exist or
        belongs to a different API key.
        """
        body = self._client._request(
            "GET", f"/v1/subscriptions/{subscription_id}"
        )
        return Subscription.from_dict(body)
 
    def update(
        self,
        subscription_id: str,
        name: str | None = None,
        is_active: bool | None = None,
        webhook_url: str | None = None,
        severity_min: str | None = None,
    ) -> Subscription:
        """
        Update a subscription.
 
        Only jurisdiction, industry, and topics are immutable —
        all other fields can be updated. Pass only the fields
        you want to change; omitted fields are left unchanged.
        """
        payload = {}
        if name is not None:
            payload["name"] = name
        if is_active is not None:
            payload["is_active"] = is_active
        if webhook_url is not None:
            payload["webhook_url"] = webhook_url
        if severity_min is not None:
            payload["severity_min"] = severity_min
 
        body = self._client._request(
            "PATCH", f"/v1/subscriptions/{subscription_id}", json=payload
        )
        return Subscription.from_dict(body)
 
    def delete(self, subscription_id: str) -> None:
        """Delete a subscription permanently."""
        self._client._request(
            "DELETE", f"/v1/subscriptions/{subscription_id}"
        )
 
    def pause(self, subscription_id: str) -> Subscription:
        """Convenience method — sets is_active=False."""
        return self.update(subscription_id, is_active=False)
 
    def resume(self, subscription_id: str) -> Subscription:
        """Convenience method — sets is_active=True."""
        return self.update(subscription_id, is_active=True)
 
 
# ── Changes Sub-API ────────────────────────────────
 
class _ChangesAPI:
    """Accessed via client.changes"""
 
    def __init__(self, client: LawhookClient):
        self._client = client
 
    def list(
        self,
        page: int = 1,
        limit: int = 20,
        jurisdiction: str | None = None,
        industry: str | None = None,
        severity: str | None = None,
    ) -> PaginatedChanges:
        """
        List regulatory changes matching your active subscriptions.
 
        Args:
            page:         page number, starting at 1
            limit:        results per page, max 100
            jurisdiction: optional filter e.g. "IN"
            industry:     optional filter e.g. "fintech"
            severity:     optional filter — "critical" | "major" | "minor"
 
        Only returns changes with status="ready".
        """
        params: dict = {"page": page, "limit": limit}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        if industry:
            params["industry"] = industry
        if severity:
            params["severity"] = severity
 
        body = self._client._request("GET", "/v1/changes", params=params)
        return PaginatedChanges.from_dict(body)
 
    def get(self, change_id: str) -> Change:
        """
        Get full detail for a single change, including
        AI-generated summary, severity, and structured diff.
 
        Raises NotFoundError if it doesn't exist or doesn't
        match any of your active subscriptions.
        """
        body = self._client._request("GET", f"/v1/changes/{change_id}")
        return Change.from_dict(body)
 
    def search(
        self,
        query: str,
        page: int = 1,
        limit: int = 20,
    ) -> PaginatedChanges:
        """
        Full-text search across change summaries, source
        authorities, and topics — within your active
        subscriptions only.
 
        Args:
            query: search term, 2-200 characters
            page:  page number, starting at 1
            limit: results per page, max 100
        """
        params = {"q": query, "page": page, "limit": limit}
        body = self._client._request(
            "GET", "/v1/changes/search", params=params
        )
        return PaginatedChanges.from_dict(body)