// tests/client.test.ts
// ─────────────────────────────────────────────────
//  Lawhook TypeScript SDK — Test Suite
//
//  Mocks globalThis.fetch so no real HTTP calls are made.
//  Run with: npm test
// ─────────────────────────────────────────────────

import { jest, describe, it, expect, beforeEach } from "@jest/globals"

import {
    LawhookClient,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ServerError,
    ConnectionError,
    LawhookError,
} from "../src/index.js"

const BASE_URL = "http://127.0.0.1:8000"
const API_KEY = "lh_live_testkey123"

// ── Mock fetch helper ──────────────────────────────

function mockFetch(
    status: number,
    body: unknown,
    headers: Record<string, string> = {},
) {
    ;(global as any).fetch = (jest.fn() as any).mockResolvedValue({
        status,
        headers: {
            get: (key: string) => headers[key.toLowerCase()] ?? null,
        },
        json: () => Promise.resolve(body),
    })
}

function mockFetchError(error: Error) {
    ;(global as any).fetch = (jest.fn() as any).mockRejectedValue(error)
}

// ── Fixtures ──────────────────────────────────────

const SUBSCRIPTION_FIXTURE = {
    id: "sub_123",
    name: "India Fintech Monitor",
    jurisdiction: "IN",
    industry: "fintech",
    topics: ["KYC", "AML"],
    webhook_url: "https://yourapp.com/webhooks",
    severity_min: "major",
    is_active: true,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    signing_secret: "whsec_abc123",
}

const CHANGE_FIXTURE = {
    id: "chg_1",
    jurisdiction: "IN",
    industry: "fintech",
    topic: "KYC",
    source_authority: "Reserve Bank of India",
    source_url: "https://rbi.org.in/circular1",
    summary: "New KYC rules introduced.",
    severity: "major",
    diff: {
        added: ["Video KYC required"],
        removed: [],
        modified: [],
    },
    status: "ready",
    effective_date: "2026-07-01",
    detected_at: "2026-06-08T13:06:53Z",
    processed_at: "2026-06-09T07:11:44Z",
}

const PAGINATED_FIXTURE = {
    items: [CHANGE_FIXTURE],
    total: 1,
    page: 1,
    limit: 20,
    has_more: false,
}

// ── Client Construction ───────────────────────────

describe("LawhookClient construction", () => {
    it("throws if apiKey is empty", () => {
        expect(() => new LawhookClient({ apiKey: "" })).toThrow("apiKey is required")
    })

    it("strips trailing slash from baseUrl", () => {
        const client = new LawhookClient({
            apiKey: API_KEY,
            baseUrl: `${BASE_URL}/`,
        })
        expect((client as unknown as { baseUrl: string }).baseUrl).toBe(BASE_URL)
    })

    it("exposes auth, subscriptions, changes namespaces", () => {
        const client = new LawhookClient({ apiKey: API_KEY, baseUrl: BASE_URL })
        expect(client.auth).toBeDefined()
        expect(client.subscriptions).toBeDefined()
        expect(client.changes).toBeDefined()
    })
})

// ── Auth ──────────────────────────────────────────

describe("client.auth", () => {
    let client: LawhookClient

    beforeEach(() => {
        client = new LawhookClient({ apiKey: API_KEY, baseUrl: BASE_URL })
    })

    it("createKey returns APIKey with key field", async () => {
        mockFetch(201, {
            id: "key_1",
            name: "my-key",
            key: "lh_live_abc123",
            key_prefix: "lh_live_abc1",
            is_active: true,
            created_at: "2026-06-01T00:00:00Z",
        })

        const key = await client.auth.createKey("my-key")

        expect(key.id).toBe("key_1")
        expect(key.key).toBe("lh_live_abc123")
        expect(key.isActive).toBe(true)
        expect(key.createdAt).toBeInstanceOf(Date)
    })

    it("listKeys returns array — key field absent", async () => {
        mockFetch(200, [
            {
                id: "key_1",
                name: "my-key",
                key_prefix: "lh_live_abc1",
                is_active: true,
                created_at: "2026-06-01T00:00:00Z",
            },
        ])

        const keys = await client.auth.listKeys()

        expect(keys).toHaveLength(1)
        expect(keys[0].key).toBeUndefined()
    })

    it("revokeKey sends DELETE and returns void", async () => {
        mockFetch(204, null)

        const result = await client.auth.revokeKey("key_1")

        expect(result).toBeUndefined()
        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining("/v1/auth/keys/key_1"),
            expect.objectContaining({ method: "DELETE" }),
        )
    })
})

// ── Subscriptions ──────────────────────────────────

describe("client.subscriptions", () => {
    let client: LawhookClient

    beforeEach(() => {
        client = new LawhookClient({ apiKey: API_KEY, baseUrl: BASE_URL })
    })

    it("create returns Subscription with signingSecret", async () => {
        mockFetch(201, SUBSCRIPTION_FIXTURE)

        const sub = await client.subscriptions.create({
            name: "India Fintech Monitor",
            jurisdiction: "IN",
            industry: "fintech",
            webhookUrl: "https://yourapp.com/webhooks",
            topics: ["KYC", "AML"],
            severityMin: "major",
        })

        expect(sub.id).toBe("sub_123")
        expect(sub.signingSecret).toBe("whsec_abc123")
        expect(sub.createdAt).toBeInstanceOf(Date)
    })

    it("update only sends provided fields", async () => {
        mockFetch(200, { ...SUBSCRIPTION_FIXTURE, name: "Renamed" })

        await client.subscriptions.update("sub_123", { name: "Renamed" })

        const call = (global as any).fetch.mock.calls[0]
        const body = JSON.parse(call[1].body)
        expect(body).toEqual({ name: "Renamed" })
        expect(body).not.toHaveProperty("is_active")
    })

    it("pause sets isActive false", async () => {
        mockFetch(200, { ...SUBSCRIPTION_FIXTURE, is_active: false })

        const sub = await client.subscriptions.pause("sub_123")
        expect(sub.isActive).toBe(false)
    })

    it("resume sets isActive true", async () => {
        mockFetch(200, { ...SUBSCRIPTION_FIXTURE, is_active: true })

        const sub = await client.subscriptions.resume("sub_123")
        expect(sub.isActive).toBe(true)
    })

    it("delete sends DELETE and returns void", async () => {
        mockFetch(204, null)

        const result = await client.subscriptions.delete("sub_123")
        expect(result).toBeUndefined()
    })
})

// ── Changes ────────────────────────────────────────

describe("client.changes", () => {
    let client: LawhookClient

    beforeEach(() => {
        client = new LawhookClient({ apiKey: API_KEY, baseUrl: BASE_URL })
    })

    it("list returns PaginatedChanges", async () => {
        mockFetch(200, PAGINATED_FIXTURE)

        const page = await client.changes.list({ jurisdiction: "IN" })

        expect(page.total).toBe(1)
        expect(page.hasMore).toBe(false)
        expect(page.items).toHaveLength(1)

        const change = page.items[0]
        expect(change.id).toBe("chg_1")
        expect(change.severity).toBe("major")
        expect(change.diff.added).toEqual(["Video KYC required"])
        expect(change.detectedAt).toBeInstanceOf(Date)
        expect(change.effectiveDate).toBeInstanceOf(Date)
    })

    it("get returns single Change — null dates handled", async () => {
        mockFetch(200, {
            ...CHANGE_FIXTURE,
            effective_date: null,
            processed_at: null,
        })

        const change = await client.changes.get("chg_1")
        expect(change.effectiveDate).toBeNull()
        expect(change.processedAt).toBeNull()
    })

    it("get handles null diff gracefully", async () => {
        mockFetch(200, { ...CHANGE_FIXTURE, diff: null })

        const change = await client.changes.get("chg_1")
        expect(change.diff.added).toEqual([])
        expect(change.diff.removed).toEqual([])
        expect(change.diff.modified).toEqual([])
    })

    it("search passes query param", async () => {
        mockFetch(200, PAGINATED_FIXTURE)

        await client.changes.search("KYC")

        const call = (global.fetch as jest.Mock).mock.calls[0]
        expect(call[0]).toContain("q=KYC")
    })

    it("list passes filters as query params", async () => {
        mockFetch(200, PAGINATED_FIXTURE)

        await client.changes.list({ jurisdiction: "IN", severity: "critical" })

        const call = (global.fetch as jest.Mock).mock.calls[0]
        expect(call[0]).toContain("jurisdiction=IN")
        expect(call[0]).toContain("severity=critical")
    })
})

// ── Error Handling ─────────────────────────────────

describe("error handling", () => {
    let client: LawhookClient

    beforeEach(() => {
        client = new LawhookClient({ apiKey: API_KEY, baseUrl: BASE_URL })
    })

    it("throws AuthenticationError on 401", async () => {
        mockFetch(401, { detail: "Invalid or missing API key." })

        await expect(client.changes.list()).rejects.toThrow(AuthenticationError)
    })

    it("throws NotFoundError on 404", async () => {
        mockFetch(404, { detail: "Change not found." })

        await expect(client.changes.get("bad_id")).rejects.toThrow(NotFoundError)
    })

    it("throws ValidationError on 422", async () => {
        mockFetch(422, { detail: "severity must be critical, major, or minor" })

        await expect(
            client.subscriptions.create({
                name: "x",
                jurisdiction: "IN",
                industry: "fintech",
                webhookUrl: "https://example.com",
                severityMin: "invalid" as never,
            }),
        ).rejects.toThrow(ValidationError)
    })

    it("throws RateLimitError on 429 with retryAfter", async () => {
        mockFetch(
            429,
            { detail: "Rate limit exceeded." },
            { "retry-after": "30" },
        )

        try {
            await client.changes.list()
        } catch (err) {
            expect(err).toBeInstanceOf(RateLimitError)
            expect((err as RateLimitError).retryAfter).toBe(30)
            expect((err as RateLimitError).statusCode).toBe(429)
        }
    })

    it("throws RateLimitError with null retryAfter if header missing", async () => {
        mockFetch(429, { detail: "Rate limit exceeded." })

        try {
            await client.changes.list()
        } catch (err) {
            expect(err).toBeInstanceOf(RateLimitError)
            expect((err as RateLimitError).retryAfter).toBeNull()
        }
    })

    it("throws ServerError on 500", async () => {
        mockFetch(500, { detail: "Internal server error" })

        await expect(client.changes.list()).rejects.toThrow(ServerError)
    })

    it("throws ConnectionError on network failure", async () => {
        mockFetchError(new Error("ECONNREFUSED"))

        await expect(client.changes.list()).rejects.toThrow(ConnectionError)
    })

    it("throws ConnectionError on timeout (AbortError)", async () => {
        const abortError = new Error("The operation was aborted")
        abortError.name = "AbortError"
        mockFetchError(abortError)

        await expect(client.changes.list()).rejects.toThrow(ConnectionError)
    })

    it("all errors are instances of LawhookError", async () => {
        const cases = [
            { status: 401, body: { detail: "Unauthorized" } },
            { status: 404, body: { detail: "Not found" } },
            { status: 422, body: { detail: "Invalid" } },
            { status: 500, body: { detail: "Server error" } },
        ]

        for (const { status, body } of cases) {
            mockFetch(status, body)
            await expect(client.changes.list()).rejects.toThrow(LawhookError)
        }
    })
})