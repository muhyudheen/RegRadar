import { useCallback, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Plus,
  Trash2,
  Pencil,
  X,
  AlertCircle,
  Copy,
  Check,
  Webhook,
  Loader,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../../lib/AuthContext';
import {
  ApiError,
  errorMessage,
  type CreateSubscriptionInput,
  type Me,
  type Severity,
  type Subscription,
  type SubscriptionWithSecret,
  type UpdateSubscriptionInput,
} from '../../../lib/apiClient';
import styles from './Subscriptions.module.css';

const JURISDICTIONS = [
  { code: 'IN', label: 'India' },
  { code: 'US', label: 'United States' },
  { code: 'SG', label: 'Singapore' },
  { code: 'AU', label: 'Australia' },
];

const SEVERITIES: Severity[] = ['minor', 'major', 'critical'];

const FORM_FIELDS = new Set([
  'name',
  'jurisdiction',
  'industry',
  'webhook_url',
  'severity_min',
  'topics',
]);

// error→string handled by shared errorMessage() from apiClient

/** count from live subscriptions, cap from /me — degrades gracefully if /me absent. */
function formatUsage(count: number, me: Me | null): string {
  if (!me) return `${count} subscription${count === 1 ? '' : 's'}`;
  if (me.subscription_limit === null) return `${count} active · unlimited`;
  return `${count} of ${me.subscription_limit} active`;
}

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

export default function Subscriptions() {
  const { client, me } = useAuth();
  const [subs, setSubs] = useState<Subscription[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Subscription | null>(null);
  const [newSecret, setNewSecret] = useState<SubscriptionWithSecret | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Subscription | null>(null);
  const [rowBusy, setRowBusy] = useState<string | null>(null);
  const [rowError, setRowError] = useState<{ id: string; msg: string } | null>(null);

  const load = useCallback(async () => {
    if (!client) return;
    setLoadError(null);
    try {
      const data = await client.getSubscriptions();
      setSubs(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load subscriptions';
      setLoadError(msg);
      setSubs([]);
    }
  }, [client]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleToggleActive(sub: Subscription) {
    if (!client) return;
    setRowBusy(sub.id);
    setRowError(null);
    try {
      const updated = await client.updateSubscription(sub.id, { is_active: !sub.is_active });
      setSubs((prev) => prev?.map((s) => (s.id === sub.id ? updated : s)) ?? null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to update';
      setRowError({ id: sub.id, msg });
    } finally {
      setRowBusy(null);
    }
  }

  async function handleDelete(sub: Subscription) {
    if (!client) return;
    setRowBusy(sub.id);
    setRowError(null);
    try {
      await client.deleteSubscription(sub.id);
      setSubs((prev) => prev?.filter((s) => s.id !== sub.id) ?? null);
      setConfirmDelete(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete';
      setRowError({ id: sub.id, msg });
    } finally {
      setRowBusy(null);
    }
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Subscriptions</h1>
          <p className={styles.subtitle}>
            {subs === null ? 'Loading…' : formatUsage(subs.length, me)}
          </p>
        </div>
        <button
          type="button"
          className={styles.primaryBtn}
          onClick={() => setShowCreate(true)}
        >
          <Plus size={14} />
          New subscription
        </button>
      </header>

      {loadError && (
        <div className={styles.banner}>
          <AlertCircle size={16} />
          <span>{loadError}</span>
        </div>
      )}

      {newSecret && (
        <SecretCallout
          subscription={newSecret}
          onDismiss={() => setNewSecret(null)}
        />
      )}

      {subs === null ? (
        <div className={styles.loadingState}>
          <Loader size={18} className={styles.spinner} />
          <span>Loading subscriptions…</span>
        </div>
      ) : subs.length === 0 ? (
        <EmptyState onCreate={() => setShowCreate(true)} />
      ) : (
        <SubscriptionTable
          subs={subs}
          rowBusy={rowBusy}
          rowError={rowError}
          onToggleActive={handleToggleActive}
          onAskDelete={(s) => setConfirmDelete(s)}
          onAskEdit={(s) => setEditing(s)}
        />
      )}

      <AnimatePresence>
        {(showCreate || editing) && (
          <SubscriptionModal
            key="sub-modal"
            mode={editing ? 'edit' : 'create'}
            initial={editing ?? undefined}
            onClose={() => {
              setShowCreate(false);
              setEditing(null);
            }}
            onCreated={(created) => {
              setShowCreate(false);
              setNewSecret(created);
              setSubs((prev) => (prev ? [created, ...prev] : [created]));
            }}
            onSaved={(updated) => {
              setEditing(null);
              setSubs((prev) => prev?.map((s) => (s.id === updated.id ? updated : s)) ?? null);
            }}
          />
        )}
        {confirmDelete && (
          <ConfirmDeleteModal
            key="confirm-delete"
            subscription={confirmDelete}
            busy={rowBusy === confirmDelete.id}
            error={rowError?.id === confirmDelete.id ? rowError.msg : null}
            onCancel={() => setConfirmDelete(null)}
            onConfirm={() => handleDelete(confirmDelete)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

/* ───────── Table ───────── */

interface TableProps {
  subs: Subscription[];
  rowBusy: string | null;
  rowError: { id: string; msg: string } | null;
  onToggleActive: (s: Subscription) => void;
  onAskDelete: (s: Subscription) => void;
  onAskEdit: (s: Subscription) => void;
}

function SubscriptionTable({
  subs,
  rowBusy,
  rowError,
  onToggleActive,
  onAskDelete,
  onAskEdit,
}: TableProps) {
  return (
    <div className={styles.tableWrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th}>Name</th>
            <th className={styles.th}>Jurisdiction</th>
            <th className={styles.th}>Industry</th>
            <th className={styles.th}>Severity</th>
            <th className={styles.th}>Created</th>
            <th className={styles.thCenter}>Active</th>
            <th className={styles.thRight}></th>
          </tr>
        </thead>
        <tbody>
          {subs.map((sub) => {
            const busy = rowBusy === sub.id;
            const err = rowError?.id === sub.id ? rowError.msg : null;
            return (
              <tr key={sub.id} className={styles.row}>
                <td className={styles.td}>
                  <div className={styles.nameCell}>
                    <span className={styles.name}>{sub.name}</span>
                    <span className={styles.webhook}>{sub.webhook_url}</span>
                    {err && <span className={styles.rowError}>{err}</span>}
                  </div>
                </td>
                <td className={styles.td} data-label="Jurisdiction">
                  <span className={styles.chip}>{sub.jurisdiction}</span>
                </td>
                <td className={styles.td} data-label="Industry">{sub.industry}</td>
                <td className={styles.td} data-label="Severity">
                  <SeverityBadge level={sub.severity_min} />
                </td>
                <td className={styles.td} data-label="Created">{formatDate(sub.created_at)}</td>
                <td className={styles.tdCenter} data-label="Active">
                  <button
                    type="button"
                    className={`${styles.toggle} ${sub.is_active ? styles.toggleOn : ''}`}
                    onClick={() => onToggleActive(sub)}
                    disabled={busy}
                    aria-label={sub.is_active ? 'Pause' : 'Resume'}
                  >
                    <span className={styles.toggleHandle} />
                  </button>
                </td>
                <td className={styles.tdRight}>
                  <div className={styles.rowActions}>
                    <button
                      type="button"
                      className={styles.iconBtn}
                      onClick={() => onAskEdit(sub)}
                      disabled={busy}
                      aria-label="Edit"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      type="button"
                      className={styles.iconBtn}
                      onClick={() => onAskDelete(sub)}
                      disabled={busy}
                      aria-label="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SeverityBadge({ level }: { level: Severity }) {
  const cls =
    level === 'critical'
      ? styles.sevCritical
      : level === 'major'
        ? styles.sevMajor
        : styles.sevMinor;
  return <span className={`${styles.sevBadge} ${cls}`}>{level}</span>;
}

/* ───────── Empty state ───────── */

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className={styles.empty}>
      <div className={styles.emptyIconWrap}>
        <Webhook size={20} />
      </div>
      <h3 className={styles.emptyTitle}>No subscriptions yet</h3>
      <p className={styles.emptyText}>
        Create your first subscription to start receiving regulatory change
        webhooks.
      </p>
      <button type="button" className={styles.primaryBtn} onClick={onCreate}>
        <Plus size={14} />
        New subscription
      </button>
    </div>
  );
}

/* ───────── Signing secret callout ───────── */

function SecretCallout({
  subscription,
  onDismiss,
}: {
  subscription: SubscriptionWithSecret;
  onDismiss: () => void;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(subscription.signing_secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* ignore */
    }
  }

  return (
    <motion.div
      className={styles.secretCallout}
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className={styles.secretHead}>
        <div>
          <h4 className={styles.secretTitle}>Signing secret — copy now</h4>
          <p className={styles.secretSub}>
            Shown only once. Use it to verify webhook signatures from{' '}
            <strong className={styles.secretStrong}>{subscription.name}</strong>.
          </p>
        </div>
        <button
          type="button"
          className={styles.iconBtn}
          onClick={onDismiss}
          aria-label="Dismiss"
        >
          <X size={16} />
        </button>
      </div>
      <div className={styles.secretRow}>
        <code className={styles.secretCode}>{subscription.signing_secret}</code>
        <button type="button" className={styles.secretCopy} onClick={copy}>
          {copied ? <Check size={14} /> : <Copy size={14} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
    </motion.div>
  );
}

/* ───────── Create / Edit modal ───────── */

function SubscriptionModal({
  mode,
  initial,
  onClose,
  onCreated,
  onSaved,
}: {
  mode: 'create' | 'edit';
  initial?: Subscription;
  onClose: () => void;
  onCreated: (s: SubscriptionWithSecret) => void;
  onSaved: (s: Subscription) => void;
}) {
  const { client } = useAuth();
  const isEdit = mode === 'edit';
  const [name, setName] = useState(initial?.name ?? '');
  const [jurisdiction, setJurisdiction] = useState(initial?.jurisdiction ?? 'IN');
  const [industry, setIndustry] = useState(initial?.industry ?? 'fintech');
  const [webhookUrl, setWebhookUrl] = useState(initial?.webhook_url ?? '');
  const [severity, setSeverity] = useState<Severity>(initial?.severity_min ?? 'major');
  const [topics, setTopics] = useState(initial?.topics?.join(', ') ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<number | null>(null);
  const [errorField, setErrorField] = useState<string | null>(null);

  const fieldErr = (n: string) => (errorField === n ? error : null);
  const fieldShown = !!errorField && FORM_FIELDS.has(errorField);

  // Mirror backend validation so we don't round-trip a 422.
  const nameValid = name.trim().length > 0;
  const severityValid = SEVERITIES.includes(severity);
  const canSubmit = useMemo(
    () =>
      nameValid &&
      severityValid &&
      (isEdit || (industry.trim().length > 0 && webhookUrl.trim().length > 0)) &&
      !busy,
    [nameValid, severityValid, isEdit, industry, webhookUrl, busy],
  );

  async function handleSubmit() {
    if (!client || !canSubmit) return;
    setBusy(true);
    setError(null);
    setErrorCode(null);
    setErrorField(null);
    try {
      if (isEdit && initial) {
        // PATCH only the editable fields that actually changed.
        const patch: UpdateSubscriptionInput = {};
        if (name.trim() !== initial.name) patch.name = name.trim();
        if (webhookUrl.trim() !== initial.webhook_url) patch.webhook_url = webhookUrl.trim();
        if (severity !== initial.severity_min) patch.severity_min = severity;
        if (Object.keys(patch).length === 0) {
          onClose();
          return;
        }
        const updated = await client.updateSubscription(initial.id, patch);
        onSaved(updated);
      } else {
        const input: CreateSubscriptionInput = {
          name: name.trim(),
          jurisdiction,
          industry: industry.trim().toLowerCase(),
          webhook_url: webhookUrl.trim(),
          severity_min: severity,
        };
        const topicList = topics.split(',').map((t) => t.trim()).filter(Boolean);
        if (topicList.length) input.topics = topicList;
        const created = await client.createSubscription(input);
        onCreated(created);
      }
    } catch (err) {
      setError(errorMessage(err));
      setErrorCode(err instanceof ApiError ? err.status : null);
      setErrorField(err instanceof ApiError ? err.field ?? null : null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <motion.div
      className={styles.overlayRight}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      onClick={onClose}
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
          <h2 className={styles.slideoverTitle}>
            {isEdit ? 'Edit subscription' : 'New subscription'}
          </h2>
          <button
            type="button"
            className={styles.iconBtn}
            onClick={onClose}
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        <div className={styles.formBody}>
          <Field label="Name" error={fieldErr('name')}>
            <input
              className={styles.input}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="RBI fintech alerts"
              autoFocus
            />
          </Field>

          <div className={styles.fieldRow}>
            <Field label="Jurisdiction" error={fieldErr('jurisdiction')}>
              <select
                className={`${styles.select} ${isEdit ? styles.inputDisabled : ''}`}
                value={jurisdiction}
                onChange={(e) => setJurisdiction(e.target.value)}
                disabled={isEdit}
              >
                {JURISDICTIONS.map((j) => (
                  <option key={j.code} value={j.code}>
                    {j.code} — {j.label}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Industry" error={fieldErr('industry')}>
              <input
                className={`${styles.input} ${isEdit ? styles.inputDisabled : ''}`}
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="fintech"
                disabled={isEdit}
              />
            </Field>
          </div>

          <Field label="Webhook URL" error={fieldErr('webhook_url')}>
            <input
              className={styles.input}
              type="url"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://api.example.com/hooks/lawhook"
            />
          </Field>

          <Field label="Minimum severity">
            <div className={styles.segment}>
              {SEVERITIES.map((s) => (
                <button
                  key={s}
                  type="button"
                  className={`${styles.segmentBtn} ${severity === s ? styles.segmentActive : ''}`}
                  onClick={() => setSeverity(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </Field>

          {!isEdit && (
            <Field label="Topics (optional, comma-separated)" error={fieldErr('topics')}>
              <input
                className={styles.input}
                value={topics}
                onChange={(e) => setTopics(e.target.value)}
                placeholder="kyc, payments"
              />
            </Field>
          )}

          {error && !fieldShown && (
            <div className={styles.errorBox}>
              <AlertCircle size={14} />
              <div>
                <p>{typeof error === 'string' ? error : 'Something went wrong'}</p>
                {errorCode === 403 && (
                  <p className={styles.errorHint}>
                    <Link to="/pricing" className={styles.errorLink}>
                      Upgrade your plan
                    </Link>{' '}
                    to add more subscriptions.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        <div className={styles.slideoverFoot}>
          <button type="button" className={styles.ghostBtn} onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className={styles.primaryBtn}
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            {busy
              ? isEdit
                ? 'Saving…'
                : 'Creating…'
              : isEdit
                ? 'Save changes'
                : 'Create subscription'}
          </button>
        </div>
      </motion.aside>
    </motion.div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string | null;
  children: React.ReactNode;
}) {
  return (
    <label className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      {children}
      {error && <span className={styles.fieldError}>{error}</span>}
    </label>
  );
}

/* ───────── Confirm delete modal ───────── */

function ConfirmDeleteModal({
  subscription,
  busy,
  error,
  onCancel,
  onConfirm,
}: {
  subscription: Subscription;
  busy: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <motion.div
      className={styles.overlay}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      onClick={onCancel}
    >
      <motion.div
        className={styles.confirmModal}
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        transition={{ duration: 0.2 }}
      >
        <h3 className={styles.confirmTitle}>Delete subscription?</h3>
        <p className={styles.confirmText}>
          <strong className={styles.confirmStrong}>{subscription.name}</strong>{' '}
          will stop receiving webhooks. This can't be undone.
        </p>
        {error && (
          <div className={styles.errorBox}>
            <AlertCircle size={14} />
            <span>{error}</span>
          </div>
        )}
        <div className={styles.confirmActions}>
          <button type="button" className={styles.ghostBtn} onClick={onCancel}>
            Cancel
          </button>
          <button
            type="button"
            className={styles.dangerBtn}
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
