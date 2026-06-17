# Lawhook Python SDK

Official Python SDK for [Lawhook](https://lawhook.dev) — the developer-first
Regulatory & Compliance Change Monitoring API.

Subscribe to a jurisdiction + industry combination, and get AI-summarized
regulatory changes delivered to your webhook the moment they're detected —
plus a typed Python client for browsing and searching the change feed.

---

## Installation

```bash
pip install lawhook
```

Requires Python 3.10+.

---

## Quick Start

```python
from lawhook import LawhookClient

client = LawhookClient(api_key="rr_live_...")

# Create a subscription
sub = client.subscriptions.create(
    name="India Fintech Monitor",
    jurisdiction="IN",
    industry="fintech",
    topics=["KYC", "AML"],
    webhook_url="https://yourapp.com/webhooks/lawhook",
    severity_min="major",
)

# IMPORTANT: signing_secret is shown only once — store it securely
print(sub.signing_secret)
```

---

## Browsing Changes

```python
# List recent changes matching your subscriptions
page = client.changes.list(jurisdiction="IN", industry="fintech")

for change in page.items:
    print(f"[{change.severity}] {change.summary}")

if page.has_more:
    next_page = client.changes.list(page=page.page + 1)
```

Filter by severity:

```python
critical_changes = client.changes.list(severity="critical")
```

Get a single change with full diff detail:

```python
change = client.changes.get("chg_5f37804038e04b27a73b")

print(change.summary)
print(change.diff.added)
print(change.diff.removed)
print(change.diff.modified)
```

Search across summaries, authorities, and topics:

```python
results = client.changes.search("KYC")
for change in results.items:
    print(change.source_authority, "-", change.summary)
```

---

## Managing Subscriptions

```python
# List all subscriptions
for sub in client.subscriptions.list():
    print(sub.id, sub.jurisdiction, sub.industry, sub.is_active)

# Pause / resume
client.subscriptions.pause(sub.id)
client.subscriptions.resume(sub.id)

# Update webhook URL or severity threshold
client.subscriptions.update(
    sub.id,
    webhook_url="https://yourapp.com/webhooks/new-endpoint",
    severity_min="critical",
)

# Delete permanently
client.subscriptions.delete(sub.id)
```

> **Note:** `jurisdiction`, `industry`, and `topics` are immutable after
> creation — they define the subscription's identity. To change them,
> delete and create a new subscription.

---

## Verifying Webhook Signatures

Every webhook is signed with HMAC-SHA256 using your subscription's
`signing_secret`. Verify incoming webhooks like this:

```python
import hmac
import hashlib

def verify_webhook(payload_body: bytes, signature_header: str,
                    timestamp_header: str, secret: str) -> bool:
    body_str = payload_body.decode("utf-8")
    signed_string = f"{timestamp_header}.{body_str}"
    expected = "sha256=" + hmac.new(
        secret.encode(), signed_string.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature_header, expected)
```

---

## Error Handling

All errors raise subclasses of `LawhookError`:

```python
from lawhook import (
    LawhookError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ServerError,
    ConnectionError,
)

try:
    change = client.changes.get("chg_does_not_exist")
except NotFoundError:
    print("That change doesn't exist or isn't in your subscriptions")
except RateLimitError as e:
    print(f"Rate limited — retry after {e.retry_after} seconds")
    time.sleep(e.retry_after or 60)
except LawhookError as e:
    print(f"Request failed: {e}")
```

| Exception | HTTP Status | Meaning |
|---|---|---|
| `AuthenticationError` | 401 | Invalid or missing API key |
| `NotFoundError` | 404 | Resource doesn't exist or isn't yours |
| `ValidationError` | 422 | Request data failed validation |
| `RateLimitError` | 429 | Rate limit exceeded — `.retry_after` has wait time |
| `ServerError` | 5xx | Error on Lawhook's side — safe to retry |
| `ConnectionError` | — | Request couldn't be sent (network/timeout) |

---

## Using a Local / Self-Hosted API

For local development against your own deployment:

```python
client = LawhookClient(
    api_key="rr_live_...",
    base_url="http://127.0.0.1:8000",
)
```

---

## Resource Management

`LawhookClient` holds a connection pool — reuse one instance across your
application, or use it as a context manager:

```python
with LawhookClient(api_key="rr_live_...") as client:
    page = client.changes.list()
    # connection automatically closed on exit
```

---

## Severity Levels

| Severity | Meaning |
|---|---|
| `critical` | Immediate action required — penalties or service impact |
| `major` | Action required within 30 days — compliance changes needed |
| `minor` | Informational — no immediate action needed |

`severity_min` on a subscription sets the **minimum** severity that
triggers a webhook. A subscription with `severity_min="major"` receives
`major` and `critical` changes, but not `minor`.

---

## Development

```bash
git clone https://github.com/muhyudheen/lawhook
cd lawhook/lawhook-python

uv venv
uv pip install -e ".[dev]"
uv run pytest
```

---

## License

MIT