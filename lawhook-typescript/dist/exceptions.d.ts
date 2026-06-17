export declare class LawhookError extends Error {
    /** HTTP status code, if applicable */
    statusCode?: number;
    /** Raw response body from the API, if available */
    response?: Record<string, unknown>;
    constructor(message: string, statusCode?: number, response?: Record<string, unknown>);
}
/** Raised on HTTP 401 — invalid or missing API key */
export declare class AuthenticationError extends LawhookError {
    constructor(message: string, response?: Record<string, unknown>);
}
/** Raised on HTTP 404 — resource doesn't exist or isn't yours */
export declare class NotFoundError extends LawhookError {
    constructor(message: string, response?: Record<string, unknown>);
}
/** Raised on HTTP 422 — request data failed validation */
export declare class ValidationError extends LawhookError {
    constructor(message: string, response?: Record<string, unknown>);
}
/**
 * Raised on HTTP 429 — rate limit exceeded.
 *
 * @example
 * try {
 *     await client.changes.list()
 * } catch (err) {
 *     if (err instanceof RateLimitError) {
 *         await new Promise(r => setTimeout(r, (err.retryAfter ?? 60) * 1000))
 *     }
 * }
 */
export declare class RateLimitError extends LawhookError {
    /** Seconds to wait before retrying, from Retry-After header */
    retryAfter: number | null;
    constructor(message: string, retryAfter?: number | null, response?: Record<string, unknown>);
}
/** Raised on HTTP 5xx — error on Lawhook's side, safe to retry */
export declare class ServerError extends LawhookError {
    constructor(message: string, statusCode: number, response?: Record<string, unknown>);
}
/**
 * Raised when the request couldn't be sent at all —
 * network failure, DNS failure, or timeout.
 * Distinct from ServerError: the request never reached
 * Lawhook's servers.
 */
export declare class ConnectionError extends LawhookError {
    constructor(message: string);
}
/**
 * Inspect an HTTP status code and throw the appropriate
 * LawhookError subclass. Called internally after every
 * request — SDK users never call this directly.
 * Does nothing if status is 2xx.
 */
export declare function throwForStatus(status: number, body: Record<string, unknown> | null, retryAfter?: number | null): void;
//# sourceMappingURL=exceptions.d.ts.map