// src/index.ts
// ─────────────────────────────────────────────────
//  Lawhook TypeScript SDK
//
//  Usage:
//      import { LawhookClient } from "lawhook"
//      const client = new LawhookClient({ apiKey: "lh_live_..." })
// ─────────────────────────────────────────────────

export { LawhookClient } from "./client.js"
export type {
    LawhookClientOptions,
    CreateSubscriptionOptions,
    UpdateSubscriptionOptions,
    ListChangesOptions,
    SearchChangesOptions,
} from "./client.js"

export {
    LawhookError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ServerError,
    ConnectionError,
} from "./exceptions.js"

export type {
    APIKey,
    Subscription,
    Change,
    ChangeDiff,
    PaginatedChanges,
    Severity,
    ChangeStatus,
} from "./models.js"