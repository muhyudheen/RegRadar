import { useCallback, useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Search, X, ExternalLink, Activity, AlertCircle, Loader } from 'lucide-react';
import { useAuth } from '../../../lib/AuthContext';
import {
  errorMessage,
  type Change,
  type ChangeDiff,
  type Severity,
} from '../../../lib/apiClient';
import styles from './ChangeFeed.module.css';
import { ChangeRow, SeverityBadge, formatDateTime } from './ChangeRow';

const JURISDICTIONS = ['IN', 'US', 'SG', 'AU'];
const SEVERITIES: Severity[] = ['minor', 'major', 'critical'];

/** Diff items are LLM-authored strings; guard against a stray non-string. */
function asText(item: unknown): string {
  return typeof item === 'string' ? item : JSON.stringify(item);
}

export default function ChangeFeed() {
  const { client } = useAuth();
  const [items, setItems] = useState<Change[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const [query, setQuery] = useState('');
  const [jurisdiction, setJurisdiction] = useState('');
  const [severity, setSeverity] = useState('');

  const [selected, setSelected] = useState<Change | null>(null);
  const [detail, setDetail] = useState<Change | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const searchActive = query.trim().length >= 2;

  const fetchPage = useCallback(
    async (targetPage: number, replace: boolean) => {
      if (!client) return;
      try {
        const res = searchActive
          ? await client.searchChanges(query.trim(), targetPage)
          : await client.getChanges({
              page: targetPage,
              jurisdiction: jurisdiction || undefined,
              severity: (severity as Severity) || undefined,
            });
        // /search ignores jurisdiction + severity → apply them client-side
        let next = res.items;
        if (searchActive) {
          if (jurisdiction) next = next.filter((c) => c.jurisdiction === jurisdiction);
          if (severity) next = next.filter((c) => c.severity === severity);
        }
        setItems((prev) => (replace || !prev ? next : [...prev, ...next]));
        setHasMore(res.has_more);
        setPage(res.page);
        setError(null);
      } catch (err) {
        setError(errorMessage(err));
        if (replace) setItems([]);
      }
    },
    [client, searchActive, query, jurisdiction, severity],
  );

  useEffect(() => {
    setItems(null);
    const t = setTimeout(() => fetchPage(1, true), searchActive ? 300 : 0);
    return () => clearTimeout(t);
  }, [fetchPage, searchActive]);

  async function loadMore() {
    setLoadingMore(true);
    await fetchPage(page + 1, false);
    setLoadingMore(false);
  }

  async function openDetail(change: Change) {
    setSelected(change);
    setDetail(change); // instant render — list already carries diff + summary
    setDetailError(null);
    if (!client) return;
    setDetailLoading(true);
    try {
      setDetail(await client.getChange(change.id));
    } catch (err) {
      setDetailError(errorMessage(err));
    } finally {
      setDetailLoading(false);
    }
  }

  function closeDetail() {
    setSelected(null);
    setDetail(null);
    setDetailError(null);
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <h1 className={styles.title}>Change Feed</h1>
        <p className={styles.subtitle}>
          Regulatory changes detected across your active subscriptions.
        </p>
      </header>

      <div className={styles.toolbar}>
        <div className={styles.searchBox}>
          <Search size={15} className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            placeholder="Search summaries, authorities, topics…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button
              className={styles.searchClear}
              onClick={() => setQuery('')}
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>

        <select
          className={styles.select}
          value={jurisdiction}
          onChange={(e) => setJurisdiction(e.target.value)}
          aria-label="Filter by jurisdiction"
        >
          <option value="">All jurisdictions</option>
          {JURISDICTIONS.map((j) => (
            <option key={j} value={j}>
              {j}
            </option>
          ))}
        </select>

        <select
          className={styles.select}
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          aria-label="Filter by severity"
        >
          <option value="">All severities</option>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className={styles.banner}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {items === null ? (
        <div className={styles.list}>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className={styles.skeletonRow}>
              <div className={styles.skeletonLine} style={{ width: '40%' }} />
              <div className={styles.skeletonLine} style={{ width: '70%' }} />
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyIconWrap}>
            <Activity size={20} />
          </div>
          <h3 className={styles.emptyTitle}>No changes detected yet</h3>
          <p className={styles.emptyText}>
            Changes appear here once they’re detected for your active subscriptions’
            jurisdiction &amp; industry.
          </p>
        </div>
      ) : (
        <>
          <div className={styles.list}>
            {items.map((c) => (
              <ChangeRow key={c.id} change={c} onClick={openDetail} />
            ))}
          </div>

          {hasMore && (
            <button className={styles.loadMore} onClick={loadMore} disabled={loadingMore}>
              {loadingMore && <Loader size={14} className={styles.spinner} />}
              {loadingMore ? 'Loading…' : 'Load more'}
            </button>
          )}
        </>
      )}

      <AnimatePresence>
        {selected && detail && (
          <motion.div
            key="change-detail"
            className={styles.overlayRight}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={closeDetail}
          >
            <motion.aside
              className={styles.panel}
              onClick={(e) => e.stopPropagation()}
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
            >
              <div className={styles.panelHead}>
                <div className={styles.panelHeadMeta}>
                  <span className={styles.chip}>{detail.jurisdiction}</span>
                  <SeverityBadge level={detail.severity} />
                  {detailLoading && <Loader size={13} className={styles.spinner} />}
                </div>
                <button className={styles.iconBtn} onClick={closeDetail} aria-label="Close">
                  <X size={16} />
                </button>
              </div>

              <div className={styles.panelBody}>
                <h2 className={styles.panelTitle}>{detail.source_authority}</h2>

                <div className={styles.metaGrid}>
                  <span className={styles.metaLabel}>Industry</span>
                  <span className={styles.metaValue}>{detail.industry}</span>
                  {detail.topic && (
                    <>
                      <span className={styles.metaLabel}>Topic</span>
                      <span className={styles.metaValue}>{detail.topic}</span>
                    </>
                  )}
                  <span className={styles.metaLabel}>Detected</span>
                  <span className={styles.metaValue}>{formatDateTime(detail.detected_at)}</span>
                  {detail.effective_date && (
                    <>
                      <span className={styles.metaLabel}>Effective</span>
                      <span className={styles.metaValue}>{detail.effective_date}</span>
                    </>
                  )}
                </div>

                <a
                  className={styles.sourceLink}
                  href={detail.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View source <ExternalLink size={13} />
                </a>

                {detail.summary && (
                  <section className={styles.section}>
                    <span className={styles.sectionLabel}>Summary</span>
                    <p className={styles.summaryText}>{detail.summary}</p>
                  </section>
                )}

                <section className={styles.section}>
                  <span className={styles.sectionLabel}>Diff</span>
                  {detailError ? (
                    <div className={styles.banner}>
                      <AlertCircle size={16} />
                      <span>{detailError}</span>
                    </div>
                  ) : (
                    <DiffView diff={detail.diff} />
                  )}
                </section>
              </div>
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function DiffView({ diff }: { diff: ChangeDiff | null }) {
  if (!diff) return <p className={styles.diffEmpty}>No structured diff for this change.</p>;

  const sections = [
    { key: 'added', label: 'Added', cls: styles.diffAdded },
    { key: 'removed', label: 'Removed', cls: styles.diffRemoved },
    { key: 'modified', label: 'Modified', cls: styles.diffModified },
  ] as const;

  const hasAny = sections.some((s) => (diff[s.key]?.length ?? 0) > 0);
  if (!hasAny) return <p className={styles.diffEmpty}>No line-level changes recorded.</p>;

  return (
    <div className={styles.diffSections}>
      {sections.map((s) => {
        const list = diff[s.key] ?? [];
        if (!list.length) return null;
        return (
          <div key={s.key} className={styles.diffSection}>
            <span className={`${styles.diffSectionLabel} ${s.cls}`}>
              {s.label} · {list.length}
            </span>
            <ul className={styles.diffList}>
              {list.map((item, i) => (
                <li key={i} className={`${styles.diffItem} ${s.cls}`}>
                  {asText(item)}
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
