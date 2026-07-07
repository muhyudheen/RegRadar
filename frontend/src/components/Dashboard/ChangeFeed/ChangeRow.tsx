import { type Change, type Severity } from '../../../lib/apiClient';
import styles from './ChangeFeed.module.css';

export function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export function SeverityBadge({ level }: { level: Severity | null }) {
  if (!level) return <span className={styles.tdDim}>—</span>;
  const cls =
    level === 'critical'
      ? styles.sevCritical
      : level === 'major'
        ? styles.sevMajor
        : styles.sevMinor;
  return <span className={`${styles.sevBadge} ${cls}`}>{level}</span>;
}

/** Shared feed row — used by Change Feed (opens panel) and Overview (navigates). */
export function ChangeRow({
  change,
  onClick,
}: {
  change: Change;
  onClick: (c: Change) => void;
}) {
  return (
    <button className={styles.row} onClick={() => onClick(change)}>
      <div className={styles.rowTop}>
        <span className={styles.chip}>{change.jurisdiction}</span>
        <span className={styles.source}>{change.source_authority}</span>
        <SeverityBadge level={change.severity} />
        <span className={styles.detectedAt}>{formatDateTime(change.detected_at)}</span>
      </div>
      <p className={styles.summaryLine}>{change.summary ?? 'No summary available.'}</p>
    </button>
  );
}
