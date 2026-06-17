// src/client.ts
// ─────────────────────────────────────────────────
//  Lawhook SDK — Client
//
//  Usage:
//      import { LawhookClient } from "lawhook"
//
//      const client = new LawhookClient({
//          apiKey: "lh_live_..."
//      })
//
//      // Subscriptions
//      const sub = await client.subscriptions.create({
//          name: "India Fintech Monitor",
//          jurisdiction: "IN",
//          industry: "fintech",
//          topics: ["KYC", "AML"],
//          webhookUrl: "https://yourapp.com/webhooks",
//          severityMin: "major",
//      })
//      console.log(sub.signingSecret) // store this — shown once
//
//      // Changes
//      const page = await client.changes.list({
//          jurisdiction: "IN",
//          severity: "major",
//      })
//      for (const change of page.items) {
//          console.log(change.severity, change.summary)
//      }
//
//  All methods throw LawhookError subclasses on failure.
//  Uses native fetch (Node 18+ / browser / Deno).
// ─────────────────────────────────────────────────
import { throwForStatus, ConnectionError } from "./exceptions.js";
import { apiKeyFromJSON, changeFromJSON, paginatedChangesFromJSON, subscriptionFromJSON, } from "./models.js";
const DEFAULT_BASE_URL = "https://api.lawhook.dev";
const DEFAULT_TIMEOUT_MS = 30_000;
const SDK_VERSION = "0.1.0";
// ── Main Client ───────────────────────────────────
export class LawhookClient {
    apiKey;
    baseUrl;
    timeoutMs;
    auth;
    subscriptions;
    changes;
    constructor(options) {
        if (!options.apiKey) {
            throw new Error("apiKey is required");
        }
        this.apiKey = options.apiKey;
        this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, "");
        this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
        this.auth = new AuthAPI(this);
        this.subscriptions = new SubscriptionsAPI(this);
        this.changes = new ChangesAPI(this);
    }
    /** @internal */
    async request(options) {
        const url = new URL(this.baseUrl + options.path);
        if (options.params) {
            for (const [k, v] of Object.entries(options.params)) {
                if (v !== undefined && v !== null) {
                    url.searchParams.set(k, String(v));
                }
            }
        }
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), this.timeoutMs);
        let response;
        try {
            response = await fetch(url.toString(), {
                method: options.method,
                headers: {
                    Authorization: `Bearer ${this.apiKey}`,
                    "Content-Type": "application/json",
                    "User-Agent": `lawhook-typescript/${SDK_VERSION}`,
                },
                body: options.body ? JSON.stringify(options.body) : undefined,
                signal: controller.signal,
            });
        }
        catch (err) {
            clearTimeout(timer);
            if (err instanceof Error && err.name === "AbortError") {
                throw new ConnectionError(`Request timed out after ${this.timeoutMs}ms`);
            }
            throw new ConnectionError(`Request failed: ${err instanceof Error ? err.message : String(err)}`);
        }
        finally {
            clearTimeout(timer);
        }
        // 204 No Content
        if (response.status === 204) {
            return undefined;
        }
        let body = null;
        try {
            body = await response.json();
        }
        catch {
            body = null;
        }
        // Handle 429 — extract Retry-After header before throwForStatus
        if (response.status === 429) {
            const retryAfterHeader = response.headers.get("Retry-After");
            const retryAfter = retryAfterHeader ? parseInt(retryAfterHeader, 10) : null;
            throwForStatus(response.status, body, isNaN(retryAfter ?? NaN) ? null : retryAfter);
        }
        throwForStatus(response.status, body);
        return body;
    }
}
// ── Auth Sub-API ──────────────────────────────────
export class AuthAPI {
    client;
    constructor(client) {
        this.client = client;
    }
    /**
     * Generate a new API key.
     * The returned `key` is shown only once — store it securely.
     */
    async createKey(name) {
        const data = await this.client.request({
            method: "POST",
            path: "/v1/auth/keys",
            body: { name },
        });
        return apiKeyFromJSON(data);
    }
    /** List all API keys. Secrets are never included in list responses. */
    async listKeys() {
        const data = await this.client.request({
            method: "GET",
            path: "/v1/auth/keys",
        });
        return data.map(apiKeyFromJSON);
    }
    /** Revoke (permanently delete) an API key by ID. */
    async revokeKey(keyId) {
        await this.client.request({
            method: "DELETE",
            path: `/v1/auth/keys/${keyId}`,
        });
    }
}
export class SubscriptionsAPI {
    client;
    constructor(client) {
        this.client = client;
    }
    /**
     * Create a new webhook subscription.
     * The returned `signingSecret` is shown only once — store it securely.
     */
    async create(options) {
        const data = await this.client.request({
            method: "POST",
            path: "/v1/subscriptions",
            body: {
                name: options.name,
                jurisdiction: options.jurisdiction,
                industry: options.industry,
                webhook_url: options.webhookUrl,
                topics: options.topics ?? null,
                severity_min: options.severityMin ?? "minor",
            },
        });
        return subscriptionFromJSON(data);
    }
    /** List all subscriptions for this API key. */
    async list() {
        const data = await this.client.request({
            method: "GET",
            path: "/v1/subscriptions",
        });
        return data.map(subscriptionFromJSON);
    }
    /**
     * Get a single subscription by ID.
     * Throws NotFoundError if it doesn't exist or belongs to a different key.
     */
    async get(subscriptionId) {
        const data = await this.client.request({
            method: "GET",
            path: `/v1/subscriptions/${subscriptionId}`,
        });
        return subscriptionFromJSON(data);
    }
    /**
     * Update a subscription.
     * Only pass the fields you want to change.
     * jurisdiction, industry, and topics are immutable.
     */
    async update(subscriptionId, options) {
        const body = {};
        if (options.name !== undefined)
            body.name = options.name;
        if (options.isActive !== undefined)
            body.is_active = options.isActive;
        if (options.webhookUrl !== undefined)
            body.webhook_url = options.webhookUrl;
        if (options.severityMin !== undefined)
            body.severity_min = options.severityMin;
        const data = await this.client.request({
            method: "PATCH",
            path: `/v1/subscriptions/${subscriptionId}`,
            body,
        });
        return subscriptionFromJSON(data);
    }
    /** Delete a subscription permanently. */
    async delete(subscriptionId) {
        await this.client.request({
            method: "DELETE",
            path: `/v1/subscriptions/${subscriptionId}`,
        });
    }
    /** Convenience — sets isActive: false */
    async pause(subscriptionId) {
        return this.update(subscriptionId, { isActive: false });
    }
    /** Convenience — sets isActive: true */
    async resume(subscriptionId) {
        return this.update(subscriptionId, { isActive: true });
    }
}
export class ChangesAPI {
    client;
    constructor(client) {
        this.client = client;
    }
    /**
     * List regulatory changes matching your active subscriptions.
     * Only returns changes with status "ready".
     */
    async list(options = {}) {
        const params = {
            page: options.page ?? 1,
            limit: options.limit ?? 20,
        };
        if (options.jurisdiction)
            params.jurisdiction = options.jurisdiction;
        if (options.industry)
            params.industry = options.industry;
        if (options.severity)
            params.severity = options.severity;
        const data = await this.client.request({
            method: "GET",
            path: "/v1/changes",
            params,
        });
        return paginatedChangesFromJSON(data);
    }
    /**
     * Get full detail for a single change — AI summary,
     * severity, structured diff.
     * Throws NotFoundError if it doesn't exist or isn't in
     * your subscriptions.
     */
    async get(changeId) {
        const data = await this.client.request({
            method: "GET",
            path: `/v1/changes/${changeId}`,
        });
        return changeFromJSON(data);
    }
    /**
     * Full-text search across change summaries, source
     * authorities, and topics — within your subscriptions only.
     */
    async search(query, options = {}) {
        const params = {
            q: query,
            page: options.page ?? 1,
            limit: options.limit ?? 20,
        };
        const data = await this.client.request({
            method: "GET",
            path: "/v1/changes/search",
            params,
        });
        return paginatedChangesFromJSON(data);
    }
}
//# sourceMappingURL=client.js.map