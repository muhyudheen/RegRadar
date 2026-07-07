import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Webhook, Activity, Plus, AlertCircle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../lib/AuthContext';
import { errorMessage, type Change, type Subscription } from '../../../lib/apiClient';
import { ChangeRow, SeverityBadge } from '../ChangeFeed/ChangeRow';
import styles from './Overview.module.css';

const PREVIEW_LIMIT = 5;

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function usageText(count: number, limit: number | null): string {
  if (limit === null) return `${count} active · unlimited`;
  return `${count} of ${limit} active`;
}

const fade = (delay: number) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay, ease: [0.4, 0, 0.2, 1] as const },
});

function SkeletonRows({ n }: { n: number }) {
  return (
    <div className={styles.skeletonList}>
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className={styles.skeletonRow}>
          <div className={styles.skeletonLine} style={{ width: '45%' }} />
          <div className={styles.skeletonLine} style={{ width: '70%' }} />
        </div>
      ))}
    </div>
  );
}

export default function Overview() {
  const { client, me, meLoading, meError } = useAuth();
  const navigate = useNavigate();
  const [subs, setSubs] = useState<Subscription[] | null>(null);
  const [changes, setChanges] = useState<Change[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!client) return;
    let active = true;
    (async () => {
      setError(null);
      try {
        const [subList, changePage] = await Promise.all([
          client.getSubscriptions(),
          client.getChanges({ limit: PREVIEW_LIMIT }),
        ]);
        if (!active) return;
        setSubs(subList);
        setChanges(changePage.items);
      } catch (err) {
        if (!active) return;
        setError(errorMessage(err));
        setSubs([]);
        setChanges([]);
      }
    })();
    return () => {
      active = false;
    };
  }, [client]);

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <h1 className={styles.title}>Overview</h1>
        <p className={styles.subtitle}>Your account at a glance.</p>
      </header>

      {error && (
        <div className={styles.banner}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* ── Card 1: Tier & usage ── */}
      <motion.section className={styles.card} {...fade(0)}>
        {meLoading ? (
          <div className={styles.stats}>
            <SkeletonRows n={1} />
          </div>
        ) : meError ? (
          <div className={styles.banner}>
            <AlertCircle size={16} />
            <span>{meError}</span>
          </div>
        ) : me ? (
          <div className={styles.stats}>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Plan</span>
              <span className={styles.statValue}>{capitalize(me.tier)}</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Subscriptions</span>
              <span className={styles.statValue}>
                {usageText(me.subscription_count, me.subscription_limit)}
              </span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Account</span>
              <span className={styles.statKey}>{me.email}</span>
            </div>
          </div>
        ) : null}
      </motion.section>

      <div className={styles.twoCol}>
        {/* ── Card 2: Active subscriptions ── */}
        <motion.section className={styles.card} {...fade(0.08)}>
          <div className={styles.cardHead}>
            <div className={styles.cardHeadLeft}>
              <Webhook size={15} className={styles.cardIcon} />
              <h2 className={styles.cardTitle}>Subscriptions</h2>
              {subs && <span className={styles.countPill}>{subs.length}</span>}
            </div>
            <Link to="/dashboard/subscriptions" className={styles.cardLink}>
              View all <ArrowRight size={13} />
            </Link>
          </div>

          {subs === null ? (
            <SkeletonRows n={3} />
          ) : subs.length === 0 ? (
            <div className={styles.emptyMini}>
              <p className={styles.emptyText}>No subscriptions yet.</p>
              <Link to="/dashboard/subscriptions" className={styles.emptyAction}>
                <Plus size={13} /> Create one
              </Link>
            </div>
          ) : (
            <div className={styles.subList}>
              {subs.slice(0, PREVIEW_LIMIT).map((s) => (
                <div key={s.id} className={styles.subRow}>
                  <div className={styles.subRowMain}>
                    <span className={styles.subName}>{s.name}</span>
                    <span className={styles.subMeta}>
                      <span className={styles.chip}>{s.jurisdiction}</span>
                      <span className={styles.subIndustry}>{s.industry}</span>
                    </span>
                  </div>
                  <SeverityBadge level={s.severity_min} />
                </div>
              ))}
            </div>
          )}
        </motion.section>

        {/* ── Card 3: Recent changes ── */}
        <motion.section className={styles.card} {...fade(0.16)}>
          <div className={styles.cardHead}>
            <div className={styles.cardHeadLeft}>
              <Activity size={15} className={styles.cardIcon} />
              <h2 className={styles.cardTitle}>Recent changes</h2>
            </div>
            <Link to="/dashboard/feed" className={styles.cardLink}>
              View all <ArrowRight size={13} />
            </Link>
          </div>

          {changes === null ? (
            <SkeletonRows n={3} />
          ) : changes.length === 0 ? (
            <div className={styles.emptyMini}>
              <p className={styles.emptyText}>No changes detected yet.</p>
              <span className={styles.emptyHint}>
                Changes appear here once detected for your subscriptions.
              </span>
            </div>
          ) : (
            <div className={styles.changeList}>
              {changes.map((c) => (
                <ChangeRow key={c.id} change={c} onClick={() => navigate('/dashboard/feed')} />
              ))}
            </div>
          )}
        </motion.section>
      </div>
    </div>
  );
}
