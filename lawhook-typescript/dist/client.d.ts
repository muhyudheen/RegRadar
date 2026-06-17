import { APIKey, Change, PaginatedChanges, Subscription, Severity } from "./models.js";
export interface LawhookClientOptions {
    /** Your Lawhook API key (starts with "lh_live_") */
    apiKey: string;
    /**
     * Override the API base URL — useful for local dev:
     *   baseUrl: "http://127.0.0.1:8000"
     */
    baseUrl?: string;
    /** Request timeout in milliseconds. Default 30000 (30s). */
    timeoutMs?: number;
}
interface RequestOptions {
    method: "GET" | "POST" | "PATCH" | "DELETE";
    path: string;
    body?: Record<string, unknown>;
    params?: Record<string, string | number | boolean>;
}
export declare class LawhookClient {
    private readonly apiKey;
    private readonly baseUrl;
    private readonly timeoutMs;
    readonly auth: AuthAPI;
    readonly subscriptions: SubscriptionsAPI;
    readonly changes: ChangesAPI;
    constructor(options: LawhookClientOptions);
    /** @internal */
    request<T>(options: RequestOptions): Promise<T>;
}
export declare class AuthAPI {
    private readonly client;
    constructor(client: LawhookClient);
    /**
     * Generate a new API key.
     * The returned `key` is shown only once — store it securely.
     */
    createKey(name: string): Promise<APIKey>;
    /** List all API keys. Secrets are never included in list responses. */
    listKeys(): Promise<APIKey[]>;
    /** Revoke (permanently delete) an API key by ID. */
    revokeKey(keyId: string): Promise<void>;
}
export interface CreateSubscriptionOptions {
    name: string;
    jurisdiction: string;
    industry: string;
    webhookUrl: string;
    topics?: string[];
    severityMin?: "minor" | "major" | "critical";
}
export interface UpdateSubscriptionOptions {
    name?: string;
    isActive?: boolean;
    webhookUrl?: string;
    severityMin?: "minor" | "major" | "critical";
}
export declare class SubscriptionsAPI {
    private readonly client;
    constructor(client: LawhookClient);
    /**
     * Create a new webhook subscription.
     * The returned `signingSecret` is shown only once — store it securely.
     */
    create(options: CreateSubscriptionOptions): Promise<Subscription>;
    /** List all subscriptions for this API key. */
    list(): Promise<Subscription[]>;
    /**
     * Get a single subscription by ID.
     * Throws NotFoundError if it doesn't exist or belongs to a different key.
     */
    get(subscriptionId: string): Promise<Subscription>;
    /**
     * Update a subscription.
     * Only pass the fields you want to change.
     * jurisdiction, industry, and topics are immutable.
     */
    update(subscriptionId: string, options: UpdateSubscriptionOptions): Promise<Subscription>;
    /** Delete a subscription permanently. */
    delete(subscriptionId: string): Promise<void>;
    /** Convenience — sets isActive: false */
    pause(subscriptionId: string): Promise<Subscription>;
    /** Convenience — sets isActive: true */
    resume(subscriptionId: string): Promise<Subscription>;
}
export interface ListChangesOptions {
    page?: number;
    limit?: number;
    jurisdiction?: string;
    industry?: string;
    severity?: Severity;
}
export interface SearchChangesOptions {
    page?: number;
    limit?: number;
}
export declare class ChangesAPI {
    private readonly client;
    constructor(client: LawhookClient);
    /**
     * List regulatory changes matching your active subscriptions.
     * Only returns changes with status "ready".
     */
    list(options?: ListChangesOptions): Promise<PaginatedChanges>;
    /**
     * Get full detail for a single change — AI summary,
     * severity, structured diff.
     * Throws NotFoundError if it doesn't exist or isn't in
     * your subscriptions.
     */
    get(changeId: string): Promise<Change>;
    /**
     * Full-text search across change summaries, source
     * authorities, and topics — within your subscriptions only.
     */
    search(query: string, options?: SearchChangesOptions): Promise<PaginatedChanges>;
}
export {};
//# sourceMappingURL=client.d.ts.map