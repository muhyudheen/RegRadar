const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/v1`
  : '/api/v1';

export type Severity = 'minor' | 'major' | 'critical';

export interface Subscription {
  id: string;
  name: string;
  jurisdiction: string;
  industry: string;
  topics?: string[];
  webhook_url: string;
  severity_min: Severity;
  is_active: boolean;
  created_at: string;
}

export interface SubscriptionWithSecret extends Subscription {
  signing_secret: string;
}

export interface CreateSubscriptionInput {
  name: string;
  jurisdiction: string;
  industry: string;
  topics?: string[];
  webhook_url: string;
  severity_min: Severity;
}

export interface UpdateSubscriptionInput {
  name?: string;
  is_active?: boolean;
  webhook_url?: string;
  severity_min?: Severity;
}

export interface ChangeDiff {
  added: string[];
  removed: string[];
  modified: string[];
}

export interface Change {
  id: string;
  jurisdiction: string;
  industry: string;
  topic: string | null;
  source_authority: string;
  source_url: string;
  summary: string | null;
  severity: Severity | null;
  diff: ChangeDiff | null;
  status: string;
  effective_date: string | null;
  detected_at: string;
  processed_at: string | null;
}

export interface PaginatedChanges {
  items: Change[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface ChangeFilters {
  page?: number;
  limit?: number;
  jurisdiction?: string;
  severity?: Severity;
}

/** GET /auth/me — the logged-in user's identity + pooled usage. */
export interface Me {
  id: string;
  email: string;
  tier: string;
  subscription_count: number;
  subscription_limit: number | null; // null = unlimited
  created_at: string;
}

/** Minimal user info returned alongside the token by signup/login. */
export interface AuthUser {
  id: string;
  email: string;
  tier: string;
}

/** POST /auth/signup and /auth/login response shape. */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

/** Returned only by POST /auth/keys — the full `key` is shown ONCE, never again. */
export interface CreatedApiKey {
  id: string;
  name: string;
  key: string;
  key_prefix: string;
  created_at: string;
}

/** List/summary shape — never contains the full key, only the prefix. */
export interface ApiKeySummary {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export class ApiError extends Error {
  status: number;
  detail: string;
  field?: string;
  constructor(status: number, detail: string, field?: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.field = field;
  }
}

export class UnauthorizedError extends ApiError {
  constructor(detail: string) {
    super(401, detail);
  }
}

/** Reduce any thrown value to a renderable string — never an object. */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.detail;
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  return 'Something went wrong';
}

async function request<T>(
  apiKey: string | null,
  path: string,
  init: RequestInit = {},
  onUnauthorized?: () => void,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((init.headers as Record<string, string>) || {}),
  };
  // Bearer is injected only for authenticated calls; public endpoints pass null.
  if (apiKey) headers.Authorization = `Bearer ${apiKey}`;

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (res.status === 401) {
    onUnauthorized?.();
    throw new UnauthorizedError('Invalid or expired API key');
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const body = await res.json().catch(() => ({}));

  if (!res.ok) {
    const raw = body?.detail ?? body?.message;
    let detail: string;
    let field: string | undefined;
    if (typeof raw === 'string') {
      detail = raw;
    } else if (raw && typeof raw === 'object') {
      // e.g. 422 → { detail: { field, error } }, or FastAPI array form
      const first = Array.isArray(raw) ? raw[0] : raw;
      detail = first?.error ?? first?.msg ?? first?.message ?? `Request failed (${res.status})`;
      field =
        first?.field ?? (Array.isArray(first?.loc) ? first.loc[first.loc.length - 1] : undefined);
    } else {
      detail = `Request failed (${res.status})`;
    }
    throw new ApiError(res.status, detail, field);
  }

  return body as T;
}

export interface ApiClient {
  getSubscriptions: () => Promise<Subscription[]>;
  getSubscription: (id: string) => Promise<Subscription>;
  createSubscription: (input: CreateSubscriptionInput) => Promise<SubscriptionWithSecret>;
  updateSubscription: (id: string, input: UpdateSubscriptionInput) => Promise<Subscription>;
  deleteSubscription: (id: string) => Promise<void>;
  getMe: () => Promise<Me>;
  getChanges: (filters?: ChangeFilters) => Promise<PaginatedChanges>;
  searchChanges: (q: string, page?: number) => Promise<PaginatedChanges>;
  getChange: (id: string) => Promise<Change>;
  getApiKeys: () => Promise<ApiKeySummary[]>;
  createApiKey: (name: string) => Promise<CreatedApiKey>;
  revokeApiKey: (id: string) => Promise<void>;
}

/**
 * Sign up a new user. UNAUTHENTICATED — returns a JWT session + user.
 */
export function signup(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>(null, '/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

/**
 * Log in. UNAUTHENTICATED — returns a JWT session + user.
 */
export function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>(null, '/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function createApiClient(apiKey: string, onUnauthorized?: () => void): ApiClient {
  return {
    getSubscriptions: () =>
      request<Subscription[]>(apiKey, '/subscriptions', { method: 'GET' }, onUnauthorized),

    getSubscription: (id) =>
      request<Subscription>(apiKey, `/subscriptions/${id}`, { method: 'GET' }, onUnauthorized),

    createSubscription: (input) =>
      request<SubscriptionWithSecret>(
        apiKey,
        '/subscriptions',
        { method: 'POST', body: JSON.stringify(input) },
        onUnauthorized,
      ),

    updateSubscription: (id, input) =>
      request<Subscription>(
        apiKey,
        `/subscriptions/${id}`,
        { method: 'PATCH', body: JSON.stringify(input) },
        onUnauthorized,
      ),

    deleteSubscription: (id) =>
      request<void>(apiKey, `/subscriptions/${id}`, { method: 'DELETE' }, onUnauthorized),

    getMe: () => request<Me>(apiKey, '/auth/me', { method: 'GET' }, onUnauthorized),

    getApiKeys: () =>
      request<ApiKeySummary[]>(apiKey, '/auth/keys', { method: 'GET' }, onUnauthorized),

    createApiKey: (name) =>
      request<CreatedApiKey>(
        apiKey,
        '/auth/keys',
        { method: 'POST', body: JSON.stringify({ name }) },
        onUnauthorized,
      ),

    revokeApiKey: (id) =>
      request<void>(apiKey, `/auth/keys/${id}`, { method: 'DELETE' }, onUnauthorized),

    getChanges: (filters = {}) => {
      const params = new URLSearchParams();
      if (filters.page) params.set('page', String(filters.page));
      if (filters.limit) params.set('limit', String(filters.limit));
      if (filters.jurisdiction) params.set('jurisdiction', filters.jurisdiction);
      if (filters.severity) params.set('severity', filters.severity);
      const qs = params.toString();
      return request<PaginatedChanges>(
        apiKey,
        `/changes${qs ? `?${qs}` : ''}`,
        { method: 'GET' },
        onUnauthorized,
      );
    },

    searchChanges: (q, page = 1) => {
      const params = new URLSearchParams({ q, page: String(page) });
      return request<PaginatedChanges>(
        apiKey,
        `/changes/search?${params.toString()}`,
        { method: 'GET' },
        onUnauthorized,
      );
    },

    getChange: (id) =>
      request<Change>(apiKey, `/changes/${id}`, { method: 'GET' }, onUnauthorized),
  };
}
