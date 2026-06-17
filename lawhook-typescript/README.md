# Lawhook TypeScript / JavaScript SDK

Official TypeScript SDK for [Lawhook](https://lawhook.dev) — the developer-first
Regulatory & Compliance Change Monitoring API.

Subscribe to a jurisdiction + industry combination, and get AI-summarized
regulatory changes delivered to your webhook the moment they're detected —
plus a typed client for browsing and searching the change feed.

Works in Node.js 18+, Deno, and the browser (uses native `fetch`).

---

## Installation

```bash
npm install lawhook
# or
yarn add lawhook
# or
pnpm add lawhook
```

---

## Quick Start

```typescript
import { LawhookClient } from "lawhook"

const client = new LawhookClient({ apiKey: "lh_live_..." })

// Create a subscription
const sub = await client.subscriptions.create({
    name: "India Fintech Monitor",
    jurisdiction: "IN",
    industry: "fintech",
    topics: ["KYC", "AML"],
    webhookUrl: "https://yourapp.com/webhooks/lawhook",
    severityMin: "major",
})

// IMPORTANT: signingSecret is shown only once — store it securely
console.log(sub.signingSecret)
```

---

## Browsing Changes

```typescript
// List recent changes matching your subscriptions
const page = await client.changes.list({ jurisdiction: "IN", industry: "fintech" })

for (const change of page.items) {
    console.log(`[${change.severity}] ${change.summary}`)
}

if (page.hasMore) {
    const nextPage = await client.changes.list({ page: page.page + 1 })
}
```

Filter by severity:

```typescript
const critical = await client.changes.list({ severity: "critical" })
```

Get a single change with full diff detail:

```typescript
const change = await client.changes.get("chg_5f37804038e04b27a73b")

console.log(change.summary)
console.log(change.diff.added)
console.log(change.diff.removed)
console.log(change.diff.modified)
```

Search across summaries, authorities, and topics:

```typescript
const results = await client.changes.search("KYC")
for (const change of results.items) {
    console.log(change.sourceAuthority, "-", change.summary)
}
```

---

## Managing Subscriptions

```typescript
// List all subscriptions
const subs = await client.subscriptions.list()
for (const sub of subs) {
    console.log(sub.id, sub.jurisdiction, sub.industry, sub.isActive)
}

// Pause / resume
await client.subscriptions.pause(sub.id)
await client.subscriptions.resume(sub.id)

// Update webhook URL or severity threshold
await client.subscriptions.update(sub.id, {
    webhookUrl: "https://yourapp.com/webhooks/new-endpoint",
    severityMin: "critical",
})

// Delete permanently
await client.subscriptions.delete(sub.id)
```

> **Note:** `jurisdiction`, `industry`, and `topics` are immutable after
> creation. To change them, delete and create a new subscription.

---

## Verifying Webhook Signatures

Every webhook is signed with HMAC-SHA256 using your subscription's
`signingSecret`. Verify incoming webhooks like this:

```typescript
import { createHmac, timingSafeEqual } from "crypto"

function verifyWebhook(
    payloadBody: string,
    signatureHeader: string,
    timestampHeader: string,
    secret: string,
): boolean {
    const signedString = `${timestampHeader}.${payloadBody}`
    const expected = "sha256=" + createHmac("sha256", secret)
        .update(signedString)
        .digest("hex")
    return timingSafeEqual(
        Buffer.from(signatureHeader),
        Buffer.from(expected),
    )
}
```

---

## Error Handling

All errors extend `LawhookError`:

```typescript
import {
    LawhookError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ServerError,
    ConnectionError,
} from "lawhook"

try {
    const change = await client.changes.get("chg_does_not_exist")
} catch (err) {
    if (err instanceof NotFoundError) {
        console.log("That change doesn't exist or isn't in your subscriptions")
    } else if (err instanceof RateLimitError) {
        console.log(`Rate limited — retry after ${err.retryAfter} seconds`)
        await new Promise(r => setTimeout(r, (err.retryAfter ?? 60) * 1000))
    } else if (err instanceof LawhookError) {
        console.log(`Request failed [${err.statusCode}]: ${err.message}`)
    }
}
```

| Exception | HTTP Status | Meaning |
|---|---|---|
| `AuthenticationError` | 401 | Invalid or missing API key |
| `NotFoundError` | 404 | Resource doesn't exist or isn't yours |
| `ValidationError` | 422 | Request data failed validation |
| `RateLimitError` | 429 | Rate limit exceeded — `.retryAfter` has wait seconds |
| `ServerError` | 5xx | Error on Lawhook's side — safe to retry |
| `ConnectionError` | — | Request couldn't be sent (network/timeout) |

---

## Client Options

```typescript
const client = new LawhookClient({
    apiKey: "lh_live_...",        // required
    baseUrl: "http://127.0.0.1:8000", // override for local dev
    timeoutMs: 30_000,            // default 30s
})
```

---

## Severity Levels

| Severity | Meaning |
|---|---|
| `critical` | Immediate action required — penalties or service impact |
| `major` | Action required within 30 days — compliance changes needed |
| `minor` | Informational — no immediate action needed |

`severityMin` on a subscription sets the **minimum** severity that
triggers a webhook. A subscription with `severityMin: "major"` receives
`major` and `critical` changes, but not `minor`.

---

## Development

```bash
git clone https://github.com/muhyudheen/lawhook
cd lawhook/lawhook-typescript

npm install
npm run build
npm test
```

---

## License

MIT