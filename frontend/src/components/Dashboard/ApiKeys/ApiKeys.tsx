import { useCallback, useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Plus, Trash2, X, AlertCircle, Loader, KeyRound } from 'lucide-react';
import { useAuth } from '../../../lib/AuthContext';
import { errorMessage, type ApiKeySummary } from '../../../lib/apiClient';
import CreateApiKey from '../../CreateApiKey/CreateApiKey';
import styles from './ApiKeys.module.css';

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return iso;
  }
}

function formatLastUsed(iso: string | null): string {
  if (!iso) return 'Never';
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return iso;
  }
}

export default function ApiKeys() {
  const { client } = useAuth();
  const [keys, setKeys] = useState<ApiKeySummary[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [confirmRevoke, setConfirmRevoke] = useState<ApiKeySummary | null>(null);
  const [rowBusy, setRowBusy] = useState<string | null>(null);
  const [rowError, setRowError] = useState<{ id: string; msg: string } | null>(null);

  const load = useCallback(async () => {
    if (!client) return;
    setLoadError(null);
    try {
      const data = await client.getApiKeys();
      // Newest first.
      data.sort((a, b) => b.created_at.localeCompare(a.created_at));
      setKeys(data);
    } catch (err) {
      setLoadError(errorMessage(err));
      setKeys([]);
    }
  }, [client]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRevoke(k: ApiKeySummary) {
    if (!client) return;
    setRowBusy(k.id);
    setRowError(null);
    try {
      await client.revokeApiKey(k.id);
      // The list endpoint returns active keys only, so flip this row locally to
      // render its revoked state until the next full refresh drops it.
      setKeys((prev) => prev?.map((x) => (x.id === k.id ? { ...x, is_active: false } : x)) ?? null);
      setConfirmRevoke(null);
    } catch (err) {
      setRowError({ id: k.id, msg: errorMessage(err) });
    } finally {
      setRowBusy(null);
    }
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>API Keys</h1>
          <p className={styles.subtitle}>
            {keys === null
              ? 'Loading…'
              : `${keys.length} key${keys.length === 1 ? '' : 's'} · full key shown only at creation`}
          </p>
        </div>
        <button type="button" className={styles.primaryBtn} onClick={() => setShowCreate(true)}>
          <Plus size={14} />
          New API key
        </button>
      </header>

      {loadError && (
        <div className={styles.banner}>
          <AlertCircle size={16} />
          <span>{loadError}</span>
        </div>
      )}

      {keys === null ? (
        <div className={styles.loadingState}>
          <Loader size={18} className={styles.spinner} />
          <span>Loading API keys…</span>
        </div>
      ) : keys.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyIconWrap}>
            <KeyRound size={20} />
          </div>
          <h3 className={styles.emptyTitle}>No API keys yet</h3>
          <p className={styles.emptyText}>
            Create a key to authenticate against the Lawhook API.
          </p>
          <button type="button" className={styles.primaryBtn} onClick={() => setShowCreate(true)}>
            <Plus size={14} />
            New API key
          </button>
        </div>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Name</th>
                <th className={styles.th}>Key</th>
                <th className={styles.th}>Created</th>
                <th className={styles.th}>Last used</th>
                <th className={styles.thRight}></th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => {
                const busy = rowBusy === k.id;
                const err = rowError?.id === k.id ? rowError.msg : null;
                return (
                  <tr
                    key={k.id}
                    className={`${styles.row} ${k.is_active ? '' : styles.rowRevoked}`}
                  >
                    <td className={styles.td}>
                      <span className={styles.name}>{k.name}</span>
                      {err && <span className={styles.rowError}>{err}</span>}
                    </td>
                    <td className={styles.td} data-label="Key">
                      <span className={styles.keyMask}>{k.key_prefix}…</span>
                    </td>
                    <td className={styles.td} data-label="Created">{formatDate(k.created_at)}</td>
                    <td className={styles.td} data-label="Last used">{formatLastUsed(k.last_used_at)}</td>
                    <td className={styles.tdRight}>
                      {k.is_active && (
                        <button
                          type="button"
                          className={styles.iconBtn}
                          onClick={() => setConfirmRevoke(k)}
                          disabled={busy}
                          aria-label="Revoke"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <AnimatePresence>
        {showCreate && (
          <motion.div
            key="create-key"
            className={styles.overlayRight}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setShowCreate(false)}
          >
            <motion.aside
              className={styles.slideover}
              onClick={(e) => e.stopPropagation()}
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
            >
              <div className={styles.slideoverHead}>
                <h2 className={styles.slideoverTitle}>New API key</h2>
                <button
                  type="button"
                  className={styles.iconBtn}
                  onClick={() => setShowCreate(false)}
                  aria-label="Close"
                >
                  <X size={16} />
                </button>
              </div>
              <div className={styles.slideoverBody}>
                <CreateApiKey
                  autoFocus
                  onCreated={() => load()}
                  onDismiss={() => setShowCreate(false)}
                />
              </div>
            </motion.aside>
          </motion.div>
        )}

        {confirmRevoke && (
          <motion.div
            key="confirm-revoke"
            className={styles.overlay}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setConfirmRevoke(null)}
          >
            <motion.div
              className={styles.confirmModal}
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.2 }}
            >
              <h3 className={styles.confirmTitle}>Revoke API key?</h3>
              <p className={styles.confirmText}>
                <strong className={styles.confirmStrong}>{confirmRevoke.name}</strong> will be
                disabled immediately. Any requests using this key will start failing. This can’t be
                undone.
              </p>
              {rowError?.id === confirmRevoke.id && (
                <div className={styles.errorBox}>
                  <AlertCircle size={14} />
                  <span>{rowError.msg}</span>
                </div>
              )}
              <div className={styles.confirmActions}>
                <button
                  type="button"
                  className={styles.ghostBtn}
                  onClick={() => setConfirmRevoke(null)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className={styles.dangerBtn}
                  onClick={() => handleRevoke(confirmRevoke)}
                  disabled={rowBusy === confirmRevoke.id}
                >
                  {rowBusy === confirmRevoke.id ? 'Revoking…' : 'Revoke key'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
