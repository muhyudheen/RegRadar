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
    statusCode;
    /** Raw response body from the API, if available */
    response;
    constructor(message, statusCode, response) {
        super(message);
        this.name = "LawhookError";
        this.statusCode = statusCode;
        this.response = response;
        // Restore prototype chain (required for extending Error in TS)
        Object.setPrototypeOf(this, new.target.prototype);
    }
}
/** Raised on HTTP 401 — invalid or missing API key */
export class AuthenticationError extends LawhookError {
    constructor(message, response) {
        super(message, 401, response);
        this.name = "AuthenticationError";
        Object.setPrototypeOf(this, new.target.prototype);
    }
}
/** Raised on HTTP 404 — resource doesn't exist or isn't yours */
export class NotFoundError extends LawhookError {
    constructor(message, response) {
        super(message, 404, response);
        this.name = "NotFoundError";
        Object.setPrototypeOf(this, new.target.prototype);
    }
}
/** Raised on HTTP 422 — request data failed validation */
export class ValidationError extends LawhookError {
    constructor(message, response) {
        super(message, 422, response);
        this.name = "ValidationError";
        Object.setPrototypeOf(this, new.target.prototype);
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
    retryAfter;
    constructor(message, retryAfter = null, response) {
        super(message, 429, response);
        this.name = "RateLimitError";
        this.retryAfter = retryAfter;
        Object.setPrototypeOf(this, new.target.prototype);
    }
}
/** Raised on HTTP 5xx — error on Lawhook's side, safe to retry */
export class ServerError extends LawhookError {
    constructor(message, statusCode, response) {
        super(message, statusCode, response);
        this.name = "ServerError";
        Object.setPrototypeOf(this, new.target.prototype);
    }
}
/**
 * Raised when the request couldn't be sent at all —
 * network failure, DNS failure, or timeout.
 * Distinct from ServerError: the request never reached
 * Lawhook's servers.
 */
export class ConnectionError extends LawhookError {
    constructor(message) {
        super(message);
        this.name = "ConnectionError";
        Object.setPrototypeOf(this, new.target.prototype);
    }
}
/**
 * Inspect an HTTP status code and throw the appropriate
 * LawhookError subclass. Called internally after every
 * request — SDK users never call this directly.
 * Does nothing if status is 2xx.
 */
export function throwForStatus(status, body, retryAfter = null) {
    if (status >= 200 && status < 300)
        return;
    const detail = typeof body?.detail === "string" ? body.detail : "Unknown error";
    if (status === 401)
        throw new AuthenticationError(detail, body ?? undefined);
    if (status === 404)
        throw new NotFoundError(detail, body ?? undefined);
    if (status === 422)
        throw new ValidationError(detail, body ?? undefined);
    if (status === 429) {
        throw new RateLimitError(detail, retryAfter, body ?? undefined);
    }
    if (status >= 500)
        throw new ServerError(detail, status, body ?? undefined);
    throw new LawhookError(detail, status, body ?? undefined);
}
//# sourceMappingURL=exceptions.js.map