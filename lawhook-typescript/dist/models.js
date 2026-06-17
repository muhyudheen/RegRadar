// src/models.ts
// ─────────────────────────────────────────────────
//  Lawhook SDK — Response Types
//
//  All types mirror the API's JSON response shapes
//  exactly. Dates are parsed from ISO 8601 strings
//  into JS Date objects by the fromJSON helpers.
// ─────────────────────────────────────────────────
// ── Helpers ───────────────────────────────────────
function parseDate(value) {
    if (!value)
        return null;
    return new Date(value);
}
export function apiKeyFromJSON(data) {
    return {
        id: data.id,
        name: data.name,
        keyPrefix: data.key_prefix,
        isActive: data.is_active,
        createdAt: parseDate(data.created_at),
        lastUsedAt: parseDate(data.last_used_at),
        revokedAt: parseDate(data.revoked_at),
        key: data.key,
    };
}
export function subscriptionFromJSON(data) {
    return {
        id: data.id,
        name: data.name,
        jurisdiction: data.jurisdiction,
        industry: data.industry,
        topics: data.topics,
        webhookUrl: data.webhook_url,
        severityMin: data.severity_min,
        isActive: data.is_active,
        createdAt: parseDate(data.created_at),
        updatedAt: parseDate(data.updated_at),
        signingSecret: data.signing_secret,
    };
}
export function changeDiffFromJSON(data) {
    if (!data)
        return { added: [], removed: [], modified: [] };
    return {
        added: data.added ?? [],
        removed: data.removed ?? [],
        modified: data.modified ?? [],
    };
}
export function changeFromJSON(data) {
    return {
        id: data.id,
        jurisdiction: data.jurisdiction,
        industry: data.industry,
        topic: data.topic ?? null,
        sourceAuthority: data.source_authority,
        sourceUrl: data.source_url,
        summary: data.summary ?? null,
        severity: data.severity ?? null,
        diff: changeDiffFromJSON(data.diff),
        status: data.status,
        effectiveDate: parseDate(data.effective_date),
        detectedAt: parseDate(data.detected_at),
        processedAt: parseDate(data.processed_at),
    };
}
export function paginatedChangesFromJSON(data) {
    return {
        items: (data.items ?? []).map(changeFromJSON),
        total: data.total,
        page: data.page,
        limit: data.limit,
        hasMore: data.has_more,
    };
}
//# sourceMappingURL=models.js.map