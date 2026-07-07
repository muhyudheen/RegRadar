import { type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../lib/AuthContext';

/**
 * Gates the dashboard: renders children only when a JWT session exists,
 * otherwise redirects to the login page. (The old paste-an-API-key screen
 * is gone — humans log in with email + password now.)
 */
export default function AuthGate({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
