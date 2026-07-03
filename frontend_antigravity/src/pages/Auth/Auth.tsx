import { useState } from 'react';
import { motion } from 'framer-motion';
import { Radar, ArrowRight, Mail, Lock } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../lib/AuthContext';
import { errorMessage } from '../../lib/apiClient';
import styles from './Auth.module.css';

const MIN_PASSWORD = 8;
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export default function Auth({ mode }: { mode: 'login' | 'signup' }) {
  const { login, signup } = useAuth();
  const navigate = useNavigate();
  const isSignup = mode === 'signup';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setError(null);

    // Client-side validation mirrors the backend so we don't round-trip a 422.
    if (isSignup) {
      if (!EMAIL_RE.test(email.trim())) {
        setError('Enter a valid email address.');
        return;
      }
      if (password.length < MIN_PASSWORD) {
        setError(`Password must be at least ${MIN_PASSWORD} characters.`);
        return;
      }
    } else if (!email.trim() || !password) {
      setError('Enter your email and password.');
      return;
    }

    setBusy(true);
    try {
      if (isSignup) {
        await signup(email.trim(), password);
      } else {
        await login(email.trim(), password);
      }
      navigate('/dashboard');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.root}>
      <div className={styles.glow} aria-hidden="true" />

      <motion.div
        className={styles.panel}
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
      >
        <Link to="/" className={styles.brand} aria-label="Lawhook home">
          <Radar className={styles.brandIcon} />
          <span className={styles.brandText}>Lawhook</span>
        </Link>

        <h1 className={styles.headline}>
          {isSignup ? 'Create your account' : 'Welcome back'}
        </h1>
        <p className={styles.sub}>
          {isSignup
            ? 'Sign up with email and password to start monitoring.'
            : 'Log in to manage your subscriptions and API keys.'}
        </p>

        <label className={styles.field}>
          <span className={styles.fieldLabel}>Email</span>
          <div className={styles.inputRow}>
            <Mail size={16} className={styles.inputIcon} />
            <input
              className={styles.input}
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (error) setError(null);
              }}
              placeholder="you@company.com"
              autoFocus
            />
          </div>
        </label>

        <label className={styles.field}>
          <span className={styles.fieldLabel}>Password</span>
          <div className={styles.inputRow}>
            <Lock size={16} className={styles.inputIcon} />
            <input
              className={styles.input}
              type="password"
              autoComplete={isSignup ? 'new-password' : 'current-password'}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (error) setError(null);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSubmit();
              }}
              placeholder={isSignup ? 'At least 8 characters' : '••••••••'}
            />
          </div>
        </label>

        {error && <p className={styles.error}>{error}</p>}

        <button
          type="button"
          className={styles.cta}
          onClick={handleSubmit}
          disabled={busy}
        >
          {busy ? 'Please wait…' : isSignup ? 'Create account' : 'Log in'}
          {!busy && <ArrowRight size={16} />}
        </button>

        <p className={styles.helper}>
          {isSignup ? (
            <>
              Already have an account?{' '}
              <Link to="/login" className={styles.helperLink}>
                Log in
              </Link>
            </>
          ) : (
            <>
              New to Lawhook?{' '}
              <Link to="/signup" className={styles.helperLink}>
                Create an account
              </Link>
            </>
          )}
        </p>
      </motion.div>
    </div>
  );
}
