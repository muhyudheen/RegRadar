export interface APIKey {
    id: string;
    name: string;
    /** Prefix shown in dashboards e.g. "lh_live_a3f8c2" */
    keyPrefix: string;
    isActive: boolean;
    createdAt: Date;
    lastUsedAt: Date | null;
    revokedAt: Date | null;
    /**
     * The full secret key — only present in the response
     * from createKey(). Never returned again. Store securely.
     */
    key?: string;
}
export declare function apiKeyFromJSON(data: Record<string, unknown>): APIKey;
export interface Subscription {
    id: string;
    name: string;
    jurisdiction: string;
    industry: string;
    topics: string[] | null;
    webhookUrl: string;
    severityMin: "minor" | "major" | "critical";
    isActive: boolean;
    createdAt: Date;
    updatedAt: Date;
    /**
     * Per-subscription HMAC-SHA256 signing secret.
     * Only present in the response from create().
     * Never returned again. Store securely.
     */
    signingSecret?: string;
}
export declare function subscriptionFromJSON(data: Record<string, unknown>): Subscription;
export interface ChangeDiff {
    added: string[];
    removed: string[];
    modified: string[];
}
export declare function changeDiffFromJSON(data: Record<string, unknown> | null | undefined): ChangeDiff;
export type Severity = "critical" | "major" | "minor";
export type ChangeStatus = "raw" | "processing" | "ready" | "failed";
export interface Change {
    id: string;
    jurisdiction: string;
    industry: string;
    topic: string | null;
    sourceAuthority: string;
    sourceUrl: string;
    summary: string | null;
    severity: Severity | null;
    diff: ChangeDiff;
    status: ChangeStatus;
    effectiveDate: Date | null;
    detectedAt: Date;
    processedAt: Date | null;
}
export declare function changeFromJSON(data: Record<string, unknown>): Change;
export interface PaginatedChanges {
    items: Change[];
    total: number;
    page: number;
    limit: number;
    hasMore: boolean;
}
export declare function paginatedChangesFromJSON(data: Record<string, unknown>): PaginatedChanges;
//# sourceMappingURL=models.d.ts.map