import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { CheckCircle } from 'lucide-react';
import styles from './FeatureHighlights.module.css';

/* ─────────────────────────────────────────────
   Data
   ───────────────────────────────────────────── */

interface Jurisdiction {
  flag: string;
  code: string;
  industry: string;
  active: boolean;
}

const JURISDICTIONS: Jurisdiction[] = [
  { flag: '🇮🇳', code: 'IN', industry: 'Fintech', active: true },
  { flag: '🇪🇺', code: 'EU', industry: 'Healthcare', active: false },
  { flag: '🇺🇸', code: 'US', industry: 'Banking', active: true },
  { flag: '🇬🇧', code: 'UK', industry: 'Insurance', active: false },
  { flag: '🇸🇬', code: 'SG', industry: 'Fintech', active: true },
  { flag: '🇦🇺', code: 'AU', industry: 'Mining', active: false },
];

/* ─────────────────────────────────────────────
   Shared animation wrapper
   ───────────────────────────────────────────── */

interface AnimatedSectionProps {
  children: React.ReactNode;
  reversed?: boolean;
}

/** Wraps each feature section with scroll-triggered animations. */
function AnimatedSection({ children, reversed = false }: AnimatedSectionProps) {
  const ref = useRef<HTMLElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section
      ref={ref}
      className={`${styles.section} ${reversed ? styles.reversed : ''}`}
    >
      <motion.div
        className={styles.inner}
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : {}}
        transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
      >
        {children}
      </motion.div>
    </section>
  );
}

/* ─────────────────────────────────────────────
   Visual 1 – Webhook Delivery Card
   ───────────────────────────────────────────── */

function WebhookVisual() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });

  const P = styles.codePunctuation;
  const K = styles.codeKey;
  const S = styles.codeString;

  return (
    <motion.div
      ref={ref}
      className={styles.webhookCard}
      initial={{ opacity: 0, x: 40 }}
      animate={isInView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.6, delay: 0.15, ease: [0.4, 0, 0.2, 1] }}
    >
      {/* Header */}
      <div className={styles.webhookHeader}>
        <span className={styles.statusDot} />
        <span className={styles.webhookUrl}>Terminal</span>
      </div>

      {/* curl command */}
      <div className={styles.codeBlock}>
        <div className={styles.codeLine}>
          <span className={K}>$</span>{' '}
          <span className={S}>curl</span>{' '}
          <span className={P}>-X POST</span>{' '}
          <span className={S}>https://api.lawhook.dev/v1/subscriptions</span>{' \\\n'}
        </div>
        <div className={styles.codeLine}>
          {'  '}<span className={P}>-H</span> <span className={S}>"Authorization: Bearer sk_live_..."</span>{' \\\n'}
        </div>
        <div className={styles.codeLine}>
          {'  '}<span className={P}>-H</span> <span className={S}>"Content-Type: application/json"</span>{' \\\n'}
        </div>
        <div className={styles.codeLine}>
          {'  '}<span className={P}>-d</span> <span className={S}>'{`'{"jurisdiction":"IN","industry":"fintech"}'`}</span>
        </div>
      </div>

      {/* Footer */}
      <div className={styles.webhookFooter}>
        <span>201 Created</span>
        <span className={styles.footerDim}>·</span>
        <span className={styles.footerDim}>Subscription active</span>
      </div>
    </motion.div>
  );
}

/* ─────────────────────────────────────────────
   Visual 2 – AI Summary Card
   ───────────────────────────────────────────── */

function AISummaryVisual() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <motion.div
      ref={ref}
      className={styles.aiCard}
      initial={{ opacity: 0, x: -40 }}
      animate={isInView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.6, delay: 0.15, ease: [0.4, 0, 0.2, 1] }}
    >
      <span className={styles.severityBadge}>CRITICAL</span>

      <p className={styles.summaryText}>
        RBI now requires video-KYC re-verification for all accounts dormant for
        more than 12 months. Effective 1 July 2026.
      </p>

      <div className={styles.diffSection}>
        <span className={styles.diffAdded}>
          Video-KYC mandatory for dormant accounts &gt;12 months
        </span>
        <span className={styles.diffRemoved}>
          Periodic KYC update via document upload sufficient
        </span>
      </div>

      <div className={styles.authorityTag}>
        <CheckCircle size={14} className={styles.verifiedIcon} />
        <span>Reserve Bank of India</span>
      </div>
    </motion.div>
  );
}

/* ─────────────────────────────────────────────
   Visual 3 – Jurisdiction Grid
   ───────────────────────────────────────────── */

function JurisdictionVisual() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <div ref={ref} className={styles.jurisdictionGrid}>
      {JURISDICTIONS.map((j, i) => (
        <motion.div
          key={j.code}
          className={styles.jurisdictionCard}
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{
            duration: 0.45,
            delay: 0.08 * i,
            ease: [0.4, 0, 0.2, 1],
          }}
        >
          <div className={styles.jurisdictionTop}>
            <span className={styles.flag}>{j.flag}</span>
            <span className={styles.countryCode}>{j.code}</span>
            {j.active && <span className={styles.activeDot} />}
          </div>
          <span className={styles.industryTag}>{j.industry}</span>
        </motion.div>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Text column helper
   ───────────────────────────────────────────── */

interface TextBlockProps {
  badge: string;
  badgeVariant: 'primary' | 'accent' | 'success';
  heading: string;
  description: string;
  /** Animation direction: positive = slide from right, negative = from left */
  slideFrom?: number;
}

function TextBlock({
  badge,
  badgeVariant,
  heading,
  description,
  slideFrom = -40,
}: TextBlockProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });

  const badgeClass =
    badgeVariant === 'primary'
      ? styles.badgePrimary
      : badgeVariant === 'accent'
        ? styles.badgeAccent
        : styles.badgeSuccess;

  return (
    <motion.div
      ref={ref}
      className={styles.textCol}
      initial={{ opacity: 0, x: slideFrom }}
      animate={isInView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
    >
      <span className={`${styles.badge} ${badgeClass}`}>{badge}</span>
      <h3 className={styles.heading}>{heading}</h3>
      <p className={styles.description}>{description}</p>
    </motion.div>
  );
}

/* ─────────────────────────────────────────────
   Main component
   ───────────────────────────────────────────── */

/**
 * FeatureHighlights – Three alternating two-column sections
 * showcasing Webhooks, AI Summaries, and Multi-Jurisdiction coverage.
 */
function FeatureHighlights() {
  return (
    <div>
      {/* ── Section 1: Webhooks (text LEFT, visual RIGHT) ── */}
      <AnimatedSection>
        <TextBlock
          badge="WEBHOOKS"
          badgeVariant="primary"
          heading="Changes delivered the moment they happen"
          description="No more manual checking. Lawhook monitors official sources and fires a signed webhook to your endpoint within minutes of detection. Every payload includes severity scoring, source links, and an effective date."
          slideFrom={-40}
        />
        <WebhookVisual />
      </AnimatedSection>

      {/* ── Section 2: AI Analysis (text RIGHT, visual LEFT) ── */}
      <AnimatedSection reversed>
        <TextBlock
          badge="AI ANALYSIS"
          badgeVariant="accent"
          heading="Dense legalese, translated instantly"
          description="Every regulatory change is processed by AI to generate a plain-language summary, severity score, and structured diff. Your team gets actionable intelligence, not walls of legal text."
          slideFrom={40}
        />
        <AISummaryVisual />
      </AnimatedSection>

      {/* ── Section 3: Coverage (text LEFT, visual RIGHT) ── */}
      <AnimatedSection>
        <TextBlock
          badge="COVERAGE"
          badgeVariant="success"
          heading="Every jurisdiction. One API."
          description="From RBI circulars to EU directives to SEC filings. Subscribe to any combination of jurisdiction and industry, and Lawhook handles the monitoring, parsing, and delivery."
          slideFrom={-40}
        />
        <JurisdictionVisual />
      </AnimatedSection>
    </div>
  );
}

export default FeatureHighlights;
