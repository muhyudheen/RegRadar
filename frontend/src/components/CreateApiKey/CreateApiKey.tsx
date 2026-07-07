import { useState, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { KeyRound, ArrowRight, Copy, Check, AlertTriangle } from 'lucide-react';
import { errorMessage, type CreatedApiKey } from '../../lib/apiClient';
import { useAuth } from '../../lib/AuthContext';
import styles from './CreateApiKey.module.css';

interface CreateApiKeyProps {
  /**
   * Fired right after a key is created. The full key is included so a caller
   * can hand off immediately (e.g. auto sign-in). Callers that only need to
   * refresh a list should ignore the secret and never store it.
   */
  onCreated?: (key: CreatedApiKey) => void;
  /** Fired when the reveal is dismissed and the full key is wiped from state. */
  onDismiss?: () => void;
  /**
   * Optional action area rendered under the revealed key. Receives the created
   * key and a `dismiss` fn. Defaults to a single "Done" button.
   */
  revealAction?: (key: CreatedApiKey, dismiss: () => void) => ReactNode;
  /** Autofocus the name input (modal/slide-over usage). */
  autoFocus?: boolean;
}

export default function CreateApiKey({
  onCreated,
  onDismiss,
  revealAction,
  autoFocus,
}: CreateApiKeyProps) {
  const { client } = useAuth();
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<CreatedApiKey | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleCreate() {
    const trimmed = name.trim();
    if (!trimmed) {
      setError('Give your key a name to continue');
      return;
    }
    if (!client) {
      setError('Your session has expired — please log in again.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const key = await client.createApiKey(trimmed);
      setCreated(key);
      onCreated?.(key);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function dismiss() {
    // The full key is wiped here and is never recoverable afterwards.
    setCreated(null);
    setName('');
    setCopied(false);
    onDismiss?.();
  }

  async function copy() {
    if (!created) return;
    try {
      await navigator.clipboard.writeText(created.key);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard unavailable — user can still select the text */
    }
  }

  /* ── Reveal: full key shown exactly once ── */
  if (created) {
    return (
      <motion.div
        className={styles.reveal}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        <div className={styles.warnHead}>
          <span className={styles.warnIcon}>
            <AlertTriangle size={16} />
          </span>
          <div>
            <h3 className={styles.revealTitle}>Copy your API key now</h3>
            <p className={styles.revealSub}>
              This is the only time <strong className={styles.revealStrong}>{created.name}</strong>’s
              full key is shown. Store it somewhere safe — you won’t be able to see
              it again.
            </p>
          </div>
        </div>

        <div className={styles.keyRow}>
          <code className={styles.keyCode}>{created.key}</code>
          <button type="button" className={styles.copyBtn} onClick={copy}>
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>

        <div className={styles.revealActions}>
          {revealAction ? (
            revealAction(created, dismiss)
          ) : (
            <button type="button" className={styles.primaryBtn} onClick={dismiss}>
              Done
            </button>
          )}
        </div>
      </motion.div>
    );
  }

  /* ── Form ── */
  return (
    <div className={styles.form}>
      <label className={styles.field}>
        <span className={styles.fieldLabel}>Key name</span>
        <div className={styles.inputRow}>
          <KeyRound size={16} className={styles.inputIcon} />
          <input
            className={styles.input}
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (error) setError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreate();
            }}
            placeholder="Production server"
            autoFocus={autoFocus}
          />
        </div>
      </label>

      {error && <p className={styles.error}>{error}</p>}

      <button
        type="button"
        className={styles.primaryBtn}
        onClick={handleCreate}
        disabled={busy}
      >
        {busy ? 'Creating…' : 'Create API key'}
        {!busy && <ArrowRight size={16} />}
      </button>
    </div>
  );
}
