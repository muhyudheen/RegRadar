import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  createApiClient,
  errorMessage,
  login as apiLogin,
  signup as apiSignup,
  type ApiClient,
  type AuthUser,
  type Me,
} from './apiClient';

interface AuthContextValue {
  /** JWT session token — in memory only (never localStorage, per project policy). */
  token: string | null;
  /** Minimal user info from login/signup. */
  user: AuthUser | null;
  /** Full identity + usage from /me. */
  me: Me | null;
  meLoading: boolean;
  meError: string | null;
  isAuthenticated: boolean;
  /** Authed API client bound to the JWT, or null when logged out. */
  client: ApiClient | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [meLoading, setMeLoading] = useState(false);
  const [meError, setMeError] = useState<string | null>(null);

  // On any 401 the client clears the session — same self-healing as before.
  const client = useMemo<ApiClient | null>(() => {
    if (!token) return null;
    return createApiClient(token, () => {
      setToken(null);
      setUser(null);
    });
  }, [token]);

  const refreshMe = useCallback(async () => {
    if (!client) return;
    setMeLoading(true);
    setMeError(null);
    try {
      setMe(await client.getMe());
    } catch (err) {
      setMeError(errorMessage(err));
    } finally {
      setMeLoading(false);
    }
  }, [client]);

  // Fetch /me whenever a session token is present; clear on logout.
  useEffect(() => {
    if (!client) {
      setMe(null);
      setMeError(null);
      setMeLoading(false);
      return;
    }
    refreshMe();
  }, [client, refreshMe]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const signup = useCallback(async (email: string, password: string) => {
    const res = await apiSignup(email, password);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setMe(null);
    setMeError(null);
  }, []);

  const value = useMemo(
    () => ({
      token,
      user,
      me,
      meLoading,
      meError,
      isAuthenticated: !!token,
      client,
      login,
      signup,
      logout,
      refreshMe,
    }),
    [token, user, me, meLoading, meError, client, login, signup, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
