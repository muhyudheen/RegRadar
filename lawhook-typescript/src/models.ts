// src/models.ts
// ─────────────────────────────────────────────────
//  Lawhook SDK — Response Types
//
//  All types mirror the API's JSON response shapes
//  exactly. Dates are parsed from ISO 8601 strings
//  into JS Date objects by the fromJSON helpers.
// ─────────────────────────────────────────────────

// ── Helpers ───────────────────────────────────────

function parseDate(value: string | null | undefined): Date | null {
    if (!value) return null
    return new Date(value)
}

// ── API Keys ──────────────────────────────────────

export interface APIKey {
    id: string
    name: string
    /** Prefix shown in dashboards e.g. "lh_live_a3f8c2" */
    keyPrefix: string
    isActive: boolean
    createdAt: Date
    lastUsedAt: Date | null
    revokedAt: Date | null
    /**
     * The full secret key — only present in the response
     * from createKey(). Never returned again. Store securely.
     */
    key?: string
}

export function apiKeyFromJSON(data: Record<string, unknown>): APIKey {
    return {
        id: data.id as string,
        name: data.name as string,
        keyPrefix: data.key_prefix as string,
        isActive: data.is_active as boolean,
        createdAt: parseDate(data.created_at as string)!,
        lastUsedAt: parseDate(data.last_used_at as string | undefined),
        revokedAt: parseDate(data.revoked_at as string | undefined),
        key: data.key as string | undefined,
    }
}

// ── Subscriptions ─────────────────────────────────

export interface Subscription {
    id: string
    name: string
    jurisdiction: string
    industry: string
    topics: string[] | null
    webhookUrl: string
    severityMin: "minor" | "major" | "critical"
    isActive: boolean
    createdAt: Date
    updatedAt: Date
    /**
     * Per-subscription HMAC-SHA256 signing secret.
     * Only present in the response from create().
     * Never returned again. Store securely.
     */
    signingSecret?: string
}

export function subscriptionFromJSON(
    data: Record<string, unknown>,
): Subscription {
    return {
        id: data.id as string,
        name: data.name as string,
        jurisdiction: data.jurisdiction as string,
        industry: data.industry as string,
        topics: data.topics as string[] | null,
        webhookUrl: data.webhook_url as string,
        severityMin: data.severity_min as "minor" | "major" | "critical",
        isActive: data.is_active as boolean,
        createdAt: parseDate(data.created_at as string)!,
        updatedAt: parseDate(data.updated_at as string)!,
        signingSecret: data.signing_secret as string | undefined,
    }
}

// ── Changes ───────────────────────────────────────

export interface ChangeDiff {
    added: string[]
    removed: string[]
    modified: string[]
}

export function changeDiffFromJSON(
    data: Record<string, unknown> | null | undefined,
): ChangeDiff {
    if (!data) return { added: [], removed: [], modified: [] }
    return {
        added: (data.added as string[]) ?? [],
        removed: (data.removed as string[]) ?? [],
        modified: (data.modified as string[]) ?? [],
    }
}

export type Severity = "critical" | "major" | "minor"
export type ChangeStatus = "raw" | "processing" | "ready" | "failed"

export interface Change {
    id: string
    jurisdiction: string
    industry: string
    topic: string | null
    sourceAuthority: string
    sourceUrl: string
    summary: string | null
    severity: Severity | null
    diff: ChangeDiff
    status: ChangeStatus
    effectiveDate: Date | null
    detectedAt: Date
    processedAt: Date | null
}

export function changeFromJSON(data: Record<string, unknown>): Change {
    return {
        id: data.id as string,
        jurisdiction: data.jurisdiction as string,
        industry: data.industry as string,
        topic: (data.topic as string | null) ?? null,
        sourceAuthority: data.source_authority as string,
        sourceUrl: data.source_url as string,
        summary: (data.summary as string | null) ?? null,
        severity: (data.severity as Severity | null) ?? null,
        diff: changeDiffFromJSON(
            data.diff as Record<string, unknown> | null,
        ),
        status: data.status as ChangeStatus,
        effectiveDate: parseDate(data.effective_date as string | undefined),
        detectedAt: parseDate(data.detected_at as string)!,
        processedAt: parseDate(data.processed_at as string | undefined),
    }
}

// ── Pagination ────────────────────────────────────

export interface PaginatedChanges {
    items: Change[]
    total: number
    page: number
    limit: number
    hasMore: boolean
}

export function paginatedChangesFromJSON(
    data: Record<string, unknown>,
): PaginatedChanges {
    return {
        items: ((data.items as Record<string, unknown>[]) ?? []).map(
            changeFromJSON,
        ),
        total: data.total as number,
        page: data.page as number,
        limit: data.limit as number,
        hasMore: data.has_more as boolean,
    }
}