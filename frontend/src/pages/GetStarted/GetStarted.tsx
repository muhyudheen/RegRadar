import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Mail, Lock } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import Navbar from '../../components/Navbar/Navbar';
import Footer from '../../components/Footer/Footer';
import CreateApiKey from '../../components/CreateApiKey/CreateApiKey';
import { useAuth } from '../../lib/AuthContext';
import { errorMessage } from '../../lib/apiClient';
import styles from './GetStarted.module.css';

const MIN_PASSWORD = 8;
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

type Stage = 'signup' | 'key';

export default function GetStarted() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [stage, setStage] = useState<Stage>('signup');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSignup() {
    setError(null);
    if (!EMAIL_RE.test(email.trim())) {
      setError('Enter a valid email address.');
      return;
    }
    if (password.length < MIN_PASSWORD) {
      setError(`Password must be at least ${MIN_PASSWORD} characters.`);
      return;
    }
    setBusy(true);
    try {
      await signup(email.trim(), password);
      // Account created + logged in — now create the first key.
      setStage('key');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Navbar />
      <main className={styles.main}>
        <motion.div
          className={styles.content}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
        >
          <span className={styles.eyebrow}>Get started</span>
          <h1 className={styles.headline}>
            {stage === 'signup' ? 'Create your account' : 'Create your first API key'}
          </h1>
          <p className={styles.sub}>
            {stage === 'signup'
              ? 'Sign up with email and password. Then generate an API key to start calling Lawhook.'
              : 'Name a key and we’ll generate it instantly. Copy it now — it’s shown only once.'}
          </p>

          <div className={styles.card}>
            {stage === 'signup' ? (
              <div className={styles.form}>
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
                      autoComplete="new-password"
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (error) setError(null);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSignup();
                      }}
                      placeholder="At least 8 characters"
                    />
                  </div>
                </label>

                {error && <p className={styles.error}>{error}</p>}

                <button
                  type="button"
                  className={styles.continueBtn}
                  onClick={handleSignup}
                  disabled={busy}
                >
                  {busy ? 'Creating account…' : 'Create account'}
                  {!busy && <ArrowRight size={16} />}
                </button>
              </div>
            ) : (
              <CreateApiKey
                autoFocus
                revealAction={(_key, dismiss) => (
                  <>
                    <button type="button" className={styles.ghostBtn} onClick={dismiss}>
                      I’ve stored it
                    </button>
                    <button
                      type="button"
                      className={styles.continueBtn}
                      onClick={() => navigate('/dashboard')}
                    >
                      Continue to dashboard
                      <ArrowRight size={16} />
                    </button>
                  </>
                )}
                onDismiss={() => navigate('/dashboard')}
              />
            )}
          </div>

          {stage === 'signup' && (
            <p className={styles.helper}>
              Already have an account?{' '}
              <Link to="/login" className={styles.helperLink}>
                Log in
              </Link>
            </p>
          )}
        </motion.div>
      </main>
      <Footer />
    </>
  );
}
