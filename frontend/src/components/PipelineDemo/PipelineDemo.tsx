import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Landmark, GitCompare, Sparkles, Webhook, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import styles from './PipelineDemo.module.css';

/* Static, read-only demo data — no live calls, no auth. */

const STAGES = [
  {
    key: 'source',
    icon: Landmark,
    label: 'Source',
    title: 'ASIC publishes a regulatory update',
  },
  {
    key: 'detected',
    icon: GitCompare,
    label: 'Detected',
    title: 'Lawhook diffs the page',
  },
  {
    key: 'ai',
    icon: Sparkles,
    label: 'AI analysis',
    title: 'Summarised and scored',
  },
  {
    key: 'webhook',
    icon: Webhook,
    label: 'Webhook',
    title: 'Delivered to your endpoint',
  },
] as const;

/* ── JSON payload (real field names / structure) ── */

function Payload() {
  const K = styles.jsonKey;
  const S = styles.jsonString;
  const P = styles.jsonPunct;
  return (
    <pre className={styles.pre}>
      <span className={P}>{'{'}</span>
      {'\n  '}
      <span className={K}>"event"</span>
      <span className={P}>:</span> <span className={S}>"regulation.changed"</span>
      <span className={P}>,</span>
      {'\n  '}
      <span className={K}>"change_id"</span>
      <span className={P}>:</span> <span className={S}>"a7f3c210-9b44-4e8a-bf12-6d0e5a1c3f97"</span>
      <span className={P}>,</span>
      {'\n  '}
      <span className={K}>"jurisdiction"</span>
      <span className={P}>:</span> <span className={S}>"AU"</span>
      <span className={P}>,</span>
      {'\n  '}
      <span className={K}>"industry"</span>
      <span className={P}>:</span> <span className={S}>"fintech"</span>
      <span className={P}>,</span>
      {'\n  '}
      <span className={K}>"severity"</span>
      <span className={P}>:</span> <span className={S}>"major"</span>
      <span className={P}>,</span>
      {'\n  '}
      <span className={K}>"summary"</span>
      <span className={P}>:</span>{' '}
      <span className={S}>"ASIC has imposed a $10.3 million penalty on Mercer Super…"</span>
      <span className={P}>,</span>
      {'\n  '}
      <span className={K}>"source"</span>
      <span className={P}>:</span> <span className={P}>{'{'}</span>
      {'\n    '}
      <span className={K}>"authority"</span>
      <span className={P}>:</span>{' '}
      <span className={S}>"Australian Securities and Investments Commission"</span>
      <span className={P}>,</span>
      {'\n    '}
      <span className={K}>"url"</span>
      <span className={P}>:</span>{' '}
      <span className={S}>"https://asic.gov.au/about-asic/newsroom/media-releases/"</span>
      {'\n  '}
      <span className={P}>{'}'}</span>
      <span className={P}>,</span>
      {'\n  '}
      <span className={K}>"diff"</span>
      <span className={P}>:</span> <span className={P}>{'{'}</span>
      {'\n    '}
      <span className={K}>"added"</span>
      <span className={P}>:</span> <span className={P}>[</span>
      <span className={S}>"$10.3M penalty against Mercer Superannuation (Australia) Ltd"</span>
      <span className={P}>]</span>
      <span className={P}>,</span>
      {'\n    '}
      <span className={K}>"removed"</span>
      <span className={P}>:</span> <span className={P}>[]</span>
      <span className={P}>,</span>
      {'\n    '}
      <span className={K}>"modified"</span>
      <span className={P}>:</span> <span className={P}>[]</span>
      {'\n  '}
      <span className={P}>{'}'}</span>
      {'\n'}
      <span className={P}>{'}'}</span>
    </pre>
  );
}

/* ── Stage card bodies ── */

function StageBody({ stageKey }: { stageKey: string }) {
  if (stageKey === 'source') {
    return (
      <div className={styles.sourceCard}>
        <div className={styles.sourceHead}>
          <span className={styles.authority}>Australian Securities &amp; Investments Commission</span>
          <span className={styles.changedPill}>page changed</span>
        </div>
        <p className={styles.sourceLine}>Media release · Enforcement</p>
        <code className={styles.sourceUrl}>asic.gov.au/newsroom/media-releases</code>
      </div>
    );
  }

  if (stageKey === 'detected') {
    return (
      <div className={styles.diffSection}>
        <span className={styles.diffAdded}>
          $10.3M penalty against Mercer Superannuation (Australia) Ltd
        </span>
        <span className={styles.diffRemoved}>No active enforcement proceedings listed</span>
      </div>
    );
  }

  if (stageKey === 'ai') {
    return (
      <div className={styles.aiCard}>
        <span className={`${styles.sevBadge} ${styles.sevMajor}`}>SEVERITY · MAJOR</span>
        <p className={styles.summaryText}>
          ASIC has imposed a $10.3 million penalty on Mercer Super for systemic failures in
          reporting significant member service issues, affecting members’ ability to access
          their entitlements.
        </p>
      </div>
    );
  }

  // webhook
  return (
    <div className={styles.jsonCard}>
      <div className={styles.jsonBar}>
        <span className={styles.jsonDot} />
        <span>POST</span>
        <span className={styles.jsonUrl}>your-app.com/webhooks/lawhook</span>
      </div>
      <Payload />
    </div>
  );
}

/* ── Stage row ── */

function Stage({
  stage,
  index,
  last,
}: {
  stage: (typeof STAGES)[number];
  index: number;
  last: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });
  const Icon = stage.icon;

  return (
    <motion.div
      ref={ref}
      className={styles.stage}
      initial={{ opacity: 0, y: 18 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.12, ease: [0.4, 0, 0.2, 1] }}
    >
      <div className={styles.rail}>
        <div className={styles.node}>
          <Icon size={17} />
        </div>
        {!last && <div className={styles.line} />}
      </div>

      <div className={styles.stageContent}>
        <span className={styles.stageLabel}>
          {String(index + 1).padStart(2, '0')} · {stage.label}
        </span>
        <h3 className={styles.stageTitle}>{stage.title}</h3>
        <StageBody stageKey={stage.key} />
      </div>
    </motion.div>
  );
}

/* ── Section ── */

export default function PipelineDemo() {
  const headRef = useRef<HTMLDivElement>(null);
  const headInView = useInView(headRef, { once: true, margin: '-60px' });

  return (
    <section className={styles.section}>
      <div className={styles.inner}>
        <motion.div
          ref={headRef}
          className={styles.header}
          initial={{ opacity: 0, y: 16 }}
          animate={headInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
        >
          <span className={styles.eyebrow}>See it in action</span>
          <h2 className={styles.heading}>One change, end to end.</h2>
          <p className={styles.sub}>
            From a regulator’s page to a signed webhook on your server — here’s a real change
            moving through Lawhook.
          </p>
        </motion.div>

        <div className={styles.pipeline}>
          {STAGES.map((stage, i) => (
            <Stage key={stage.key} stage={stage} index={i} last={i === STAGES.length - 1} />
          ))}
        </div>

        <motion.div
          className={styles.cta}
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
        >
          <Link to="/get-started" className="btn btn-primary btn-lg">
            Get your API key
            <ArrowRight size={16} />
          </Link>
          <Link to="/docs" className={styles.quickstartLink}>
            Read the quickstart
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
