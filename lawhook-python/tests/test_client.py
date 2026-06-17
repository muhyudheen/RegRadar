# tests/test_client.py
# ─────────────────────────────────────────────────
#  Lawhook SDK — Test Suite
#
#  Uses pytest-httpx to mock HTTP responses — no real
#  API server needed. Run with:
#
#      uv run pytest
#
#  Covers:
#    - Successful requests (subscriptions, changes, search)
#    - Each exception type (401, 404, 422, 429, 500)
#    - RateLimitError.retry_after parsing from header
#    - Pagination (has_more logic)
#    - Model parsing (datetime, ChangeDiff)
#    - Context manager (__enter__/__exit__)
# ─────────────────────────────────────────────────

import pytest

from lawhook import (
    AuthenticationError,
    ChangeDiff,
    ConnectionError,
    LawhookClient,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)

BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture
def client():
    """A LawhookClient pointed at a local test server URL."""
    c = LawhookClient(api_key="rr_live_testkey", base_url=BASE_URL)
    yield c
    c.close()


# ── Client Construction ───────────────────────────

def test_requires_api_key():
    with pytest.raises(ValueError):
        LawhookClient(api_key="")


def test_context_manager():
    with LawhookClient(api_key="rr_live_testkey", base_url=BASE_URL) as c:
        assert c._api_key == "rr_live_testkey"
    # __exit__ should have closed the underlying http client
    assert c._http.is_closed


def test_base_url_trailing_slash_stripped():
    c = LawhookClient(api_key="rr_live_testkey", base_url="http://example.com/")
    assert c._base_url == "http://example.com"
    c.close()


# ── Subscriptions ──────────────────────────────────

def test_create_subscription(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/v1/subscriptions",
        json={
            "id": "sub_123",
            "name": "India Fintech Monitor",
            "jurisdiction": "IN",
            "industry": "fintech",
            "topics": ["KYC", "AML"],
            "webhook_url": "https://yourapp.com/webhooks",
            "severity_min": "major",
            "is_active": True,
            "created_at": "2026-06-01T00:00:00Z",
            "updated_at": "2026-06-01T00:00:00Z",
            "signing_secret": "whsec_abc123",
        },
        status_code=201,
    )

    sub = client.subscriptions.create(
        name="India Fintech Monitor",
        jurisdiction="IN",
        industry="fintech",
        webhook_url="https://yourapp.com/webhooks",
        topics=["KYC", "AML"],
        severity_min="major",
    )

    assert sub.id == "sub_123"
    assert sub.jurisdiction == "IN"
    assert sub.topics == ["KYC", "AML"]
    assert sub.signing_secret == "whsec_abc123"


def test_list_subscriptions(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/v1/subscriptions",
        json=[
            {
                "id": "sub_1",
                "name": "Sub One",
                "jurisdiction": "IN",
                "industry": "fintech",
                "topics": None,
                "webhook_url": "https://example.com/hook1",
                "severity_min": "minor",
                "is_active": True,
                "created_at": "2026-06-01T00:00:00Z",
                "updated_at": "2026-06-01T00:00:00Z",
            },
            {
                "id": "sub_2",
                "name": "Sub Two",
                "jurisdiction": "US",
                "industry": "banking",
                "topics": ["AML"],
                "webhook_url": "https://example.com/hook2",
                "severity_min": "critical",
                "is_active": False,
                "created_at": "2026-06-02T00:00:00Z",
                "updated_at": "2026-06-02T00:00:00Z",
            },
        ],
    )

    subs = client.subscriptions.list()

    assert len(subs) == 2
    assert subs[0].id == "sub_1"
    assert subs[0].signing_secret is None  # not present on list
    assert subs[1].is_active is False


def test_update_subscription_only_sends_provided_fields(client, httpx_mock):
    httpx_mock.add_response(
        method="PATCH",
        url=f"{BASE_URL}/v1/subscriptions/sub_123",
        json={
            "id": "sub_123",
            "name": "Renamed",
            "jurisdiction": "IN",
            "industry": "fintech",
            "topics": ["KYC"],
            "webhook_url": "https://example.com/hook",
            "severity_min": "minor",
            "is_active": True,
            "created_at": "2026-06-01T00:00:00Z",
            "updated_at": "2026-06-03T00:00:00Z",
        },
    )

    sub = client.subscriptions.update("sub_123", name="Renamed")

    assert sub.name == "Renamed"

    # Verify only "name" was sent in the request body
    request = httpx_mock.get_requests()[0]
    import json
    body = json.loads(request.content)
    assert body == {"name": "Renamed"}


def test_pause_and_resume(client, httpx_mock):
    def make_response(is_active: bool):
        return {
            "id": "sub_123",
            "name": "Sub",
            "jurisdiction": "IN",
            "industry": "fintech",
            "topics": None,
            "webhook_url": "https://example.com/hook",
            "severity_min": "minor",
            "is_active": is_active,
            "created_at": "2026-06-01T00:00:00Z",
            "updated_at": "2026-06-01T00:00:00Z",
        }

    httpx_mock.add_response(
        method="PATCH",
        url=f"{BASE_URL}/v1/subscriptions/sub_123",
        json=make_response(False),
    )
    paused = client.subscriptions.pause("sub_123")
    assert paused.is_active is False

    httpx_mock.add_response(
        method="PATCH",
        url=f"{BASE_URL}/v1/subscriptions/sub_123",
        json=make_response(True),
    )
    resumed = client.subscriptions.resume("sub_123")
    assert resumed.is_active is True


def test_delete_subscription_204(client, httpx_mock):
    httpx_mock.add_response(
        method="DELETE",
        url=f"{BASE_URL}/v1/subscriptions/sub_123",
        status_code=204,
    )

    result = client.subscriptions.delete("sub_123")
    assert result is None


# ── Changes ────────────────────────────────────────

def test_list_changes_with_filters(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=(
            f"{BASE_URL}/v1/changes"
            "?page=1&limit=20&jurisdiction=IN&industry=fintech&severity=major"
        ),
        json={
            "items": [
                {
                    "id": "chg_1",
                    "jurisdiction": "IN",
                    "industry": "fintech",
                    "topic": "KYC",
                    "source_authority": "Reserve Bank of India",
                    "source_url": "https://rbi.org.in/circular1",
                    "summary": "New KYC rules.",
                    "severity": "major",
                    "diff": {
                        "added": ["Video KYC required"],
                        "removed": [],
                        "modified": [],
                    },
                    "status": "ready",
                    "effective_date": "2026-07-01",
                    "detected_at": "2026-06-08T13:06:53.174976Z",
                    "processed_at": "2026-06-09T07:11:44.899958Z",
                }
            ],
            "total": 1,
            "page": 1,
            "limit": 20,
            "has_more": False,
        },
    )

    page = client.changes.list(
        jurisdiction="IN", industry="fintech", severity="major"
    )

    assert page.total == 1
    assert page.has_more is False
    assert len(page.items) == 1

    change = page.items[0]
    assert change.id == "chg_1"
    assert change.severity == "major"
    assert isinstance(change.diff, ChangeDiff)
    assert change.diff.added == ["Video KYC required"]
    assert change.effective_date.isoformat() == "2026-07-01"
    assert change.detected_at.year == 2026


def test_list_changes_default_params(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/v1/changes?page=1&limit=20",
        json={"items": [], "total": 0, "page": 1, "limit": 20, "has_more": False},
    )

    page = client.changes.list()
    assert page.items == []
    assert page.total == 0


def test_get_change(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/v1/changes/chg_1",
        json={
            "id": "chg_1",
            "jurisdiction": "IN",
            "industry": "fintech",
            "topic": "KYC",
            "source_authority": "Reserve Bank of India",
            "source_url": "https://rbi.org.in/circular1",
            "summary": "New KYC rules.",
            "severity": "major",
            "diff": None,
            "status": "ready",
            "effective_date": None,
            "detected_at": "2026-06-08T13:06:53.174976Z",
            "processed_at": None,
        },
    )

    change = client.changes.get("chg_1")

    assert change.id == "chg_1"
    assert change.effective_date is None
    assert change.processed_at is None
    # diff=None should still produce an empty ChangeDiff, not crash
    assert change.diff.added == []
    assert change.diff.removed == []
    assert change.diff.modified == []


def test_search_changes(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/v1/changes/search?q=KYC&page=1&limit=20",
        json={
            "items": [
                {
                    "id": "chg_1",
                    "jurisdiction": "IN",
                    "industry": "fintech",
                    "topic": "KYC",
                    "source_authority": "Reserve Bank of India",
                    "source_url": "https://rbi.org.in/circular1",
                    "summary": "KYC update.",
                    "severity": "minor",
                    "diff": {"added": [], "removed": [], "modified": []},
                    "status": "ready",
                    "effective_date": None,
                    "detected_at": "2026-06-08T13:06:53.174976Z",
                    "processed_at": "2026-06-09T07:11:44.899958Z",
                }
            ],
            "total": 1,
            "page": 1,
            "limit": 20,
            "has_more": False,
        },
    )

    results = client.changes.search("KYC")

    assert results.total == 1
    assert results.items[0].topic == "KYC"


# ── Error Handling ─────────────────────────────────

def test_authentication_error(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/v1/changes?page=1&limit=20",
        json={"detail": "Invalid or missing API key."},
        status_code=401,
    )

    with pytest.raises(AuthenticationError) as exc_info:
        client.changes.list()

    assert exc_info.value.status_code == 401
    assert "Invalid or missing API key" in str(exc_info.value)


def test_not_found_error(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/v1/changes/does_not_exist",
        json={"detail": "Change not found."},
        status_code=404,
    )

    with pytest.raises(NotFoundError) as exc_info:
        client.changes.get("does_not_exist")

    assert exc_info.value.status_code == 404


def test_validation_error(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/v1/subscriptions",
        json={"detail": "severity_min must be one of: minor, major, critical"},
        status_code=422,
    )

    with pytest.raises(ValidationError) as exc_info:
        client.subscriptions.create(
            name="Bad Sub",
            jurisdiction="IN",
            industry="fintech",
            webhook_url="https://example.com/hook",
            severity_min="invalid",
        )

    assert exc_info.value.status_code == 422


def test_rate_limit_error_with_retry_after(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/v1/changes?page=1&limit=20",
        json={"detail": "Rate limit exceeded. Try again in 30 seconds."},
        status_code=429,
        headers={"Retry-After": "30"},
    )

    with pytest.raises(RateLimitError) as exc_info:
        client.changes.list()

    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after == 30


def test_rate_limit_error_without_retry_after_header(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/v1/changes?page=1&limit=20",
        json={"detail": "Rate limit exceeded."},
        status_code=429,
        # no Retry-After header
    )

    with pytest.raises(RateLimitError) as exc_info:
        client.changes.list()

    assert exc_info.value.retry_after is None


def test_server_error(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/v1/changes?page=1&limit=20",
        json={"detail": "Internal server error"},
        status_code=500,
    )

    with pytest.raises(ServerError) as exc_info:
        client.changes.list()

    assert exc_info.value.status_code == 500


def test_connection_error_on_timeout(client, httpx_mock):
    import httpx as httpx_module

    httpx_mock.add_exception(httpx_module.TimeoutException("timed out"))

    with pytest.raises(ConnectionError):
        client.changes.list()


# ── Auth Sub-API ───────────────────────────────────

def test_create_key(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/v1/auth/keys",
        json={
            "id": "key_123",
            "name": "my-first-key",
            "key": "rr_live_abc123",
            "key_prefix": "rr_live_abc1",
            "is_active": True,
            "created_at": "2026-06-01T00:00:00Z",
        },
        status_code=201,
    )

    key = client.auth.create_key("my-first-key")

    assert key.key == "rr_live_abc123"
    assert key.is_active is True


def test_list_keys_no_secret(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/v1/auth/keys",
        json=[
            {
                "id": "key_123",
                "name": "my-first-key",
                "key_prefix": "rr_live_abc1",
                "is_active": True,
                "created_at": "2026-06-01T00:00:00Z",
            }
        ],
    )

    keys = client.auth.list_keys()

    assert len(keys) == 1
    assert keys[0].key is None  # secret never returned in list


def test_revoke_key(client, httpx_mock):
    httpx_mock.add_response(
        method="DELETE",
        url=f"{BASE_URL}/v1/auth/keys/key_123",
        status_code=204,
    )

    client.auth.revoke_key("key_123")  # should not raise