// src/exceptions.ts
// ─────────────────────────────────────────────────
//  Lawhook SDK — Exception Hierarchy
//
//  All SDK errors extend LawhookError so callers
//  can catch broadly or specifically:
//
//      try {
//          await client.changes.list()
//      } catch (err) {
//          if (err instanceof RateLimitError) {
//              await sleep(err.retryAfter * 1000)
//          } else if (err instanceof LawhookError) {
//              console.error(err.message)
//          }
//      }
// ─────────────────────────────────────────────────

export class LawhookError extends Error {
    /** HTTP status code, if applicable */
    statusCode?: number
    /** Raw response body from the API, if available */
    response?: Record<string, unknown>

    constructor(
        message: string,
        statusCode?: number,
        response?: Record<string, unknown>,
    ) {
        super(message)
        this.name = "LawhookError"
        this.statusCode = statusCode
        this.response = response
        // Restore prototype chain (required for extending Error in TS)
        Object.setPrototypeOf(this, new.target.prototype)
    }
}

/** Raised on HTTP 401 — invalid or missing API key */
export class AuthenticationError extends LawhookError {
    constructor(message: string, response?: Record<string, unknown>) {
        super(message, 401, response)
        this.name = "AuthenticationError"
        Object.setPrototypeOf(this, new.target.prototype)
    }
}

/** Raised on HTTP 404 — resource doesn't exist or isn't yours */
export class NotFoundError extends LawhookError {
    constructor(message: string, response?: Record<string, unknown>) {
        super(message, 404, response)
        this.name = "NotFoundError"
        Object.setPrototypeOf(this, new.target.prototype)
    }
}

/** Raised on HTTP 422 — request data failed validation */
export class ValidationError extends LawhookError {
    constructor(message: string, response?: Record<string, unknown>) {
        super(message, 422, response)
        this.name = "ValidationError"
        Object.setPrototypeOf(this, new.target.prototype)
    }
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
export class RateLimitError extends LawhookError {
    /** Seconds to wait before retrying, from Retry-After header */
    retryAfter: number | null

    constructor(
        message: string,
        retryAfter: number | null = null,
        response?: Record<string, unknown>,
    ) {
        super(message, 429, response)
        this.name = "RateLimitError"
        this.retryAfter = retryAfter
        Object.setPrototypeOf(this, new.target.prototype)
    }
}

/** Raised on HTTP 5xx — error on Lawhook's side, safe to retry */
export class ServerError extends LawhookError {
    constructor(
        message: string,
        statusCode: number,
        response?: Record<string, unknown>,
    ) {
        super(message, statusCode, response)
        this.name = "ServerError"
        Object.setPrototypeOf(this, new.target.prototype)
    }
}

/**
 * Raised when the request couldn't be sent at all —
 * network failure, DNS failure, or timeout.
 * Distinct from ServerError: the request never reached
 * Lawhook's servers.
 */
export class ConnectionError extends LawhookError {
    constructor(message: string) {
        super(message)
        this.name = "ConnectionError"
        Object.setPrototypeOf(this, new.target.prototype)
    }
}

/**
 * Inspect an HTTP status code and throw the appropriate
 * LawhookError subclass. Called internally after every
 * request — SDK users never call this directly.
 * Does nothing if status is 2xx.
 */
export function throwForStatus(
    status: number,
    body: Record<string, unknown> | null,
    retryAfter: number | null = null,
): void {
    if (status >= 200 && status < 300) return

    const detail =
        typeof body?.detail === "string" ? body.detail : "Unknown error"

    if (status === 401) throw new AuthenticationError(detail, body ?? undefined)
    if (status === 404) throw new NotFoundError(detail, body ?? undefined)
    if (status === 422) throw new ValidationError(detail, body ?? undefined)
    if (status === 429) {
        throw new RateLimitError(detail, retryAfter, body ?? undefined)
    }
    if (status >= 500) throw new ServerError(detail, status, body ?? undefined)

    throw new LawhookError(detail, status, body ?? undefined)
}