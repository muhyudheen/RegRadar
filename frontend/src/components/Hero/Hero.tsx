import { motion } from 'framer-motion';
import { ArrowRight, BookOpen } from 'lucide-react';
import { Link } from 'react-router-dom';
import styles from './Hero.module.css';

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.7, delay, ease: [0.25, 0.46, 0.45, 0.94] as const },
});

function WebhookPayload() {
  const K = styles.jsonKey;
  const S = styles.jsonString;
  const P = styles.jsonPunctuation;

  return (
    <pre>
      <span className={P}>{'{'}</span>{'\n'}
      {'  '}<span className={K}>"event"</span><span className={P}>:</span> <span className={S}>"regulation.changed"</span><span className={P}>,</span>{'\n'}
      {'  '}<span className={K}>"severity"</span><span className={P}>:</span> <span className={S}>"critical"</span><span className={P}>,</span>{'\n'}
      {'  '}<span className={K}>"jurisdiction"</span><span className={P}>:</span> <span className={S}>"IN"</span><span className={P}>,</span>{'\n'}
      {'  '}<span className={K}>"summary"</span><span className={P}>:</span> <span className={S}>"RBI mandates video-KYC re-verification..."</span><span className={P}>,</span>{'\n'}
      {'  '}<span className={K}>"effective_date"</span><span className={P}>:</span> <span className={S}>"2026-07-01"</span>{'\n'}
      <span className={P}>{'}'}</span>
    </pre>
  );
}

export default function Hero() {
  return (
    <section className={styles.hero}>
      <div className={styles.primaryGlow} aria-hidden="true" />
      <div className={styles.accentGlow} aria-hidden="true" />

      <div className={styles.content}>
        <motion.h1 className={styles.headline} {...fadeUp(0)}>
          Regulatory changes.{' '}
          <br />
          Delivered instantly.
        </motion.h1>

        <motion.p className={styles.subheadline} {...fadeUp(0.15)}>
          Subscribe to jurisdictions and industries. Get structured webhook
          payloads with AI summaries, severity scores, and diffs — the moment
          regulations change.
        </motion.p>

        <motion.div className={styles.ctas} {...fadeUp(0.3)}>
          <Link to="/dashboard" className="btn btn-primary btn-lg">
            Start Free
            <ArrowRight size={16} />
          </Link>
          <Link to="/docs" className="btn btn-ghost btn-lg">
            <BookOpen size={16} />
            Documentation
          </Link>
        </motion.div>

        <motion.div className={styles.codeCard} {...fadeUp(0.5)}>
          <div className={styles.terminalBar}>
            <span className={styles.dotRed} />
            <span className={styles.dotYellow} />
            <span className={styles.dotGreen} />
            <span className={styles.terminalTitle}>webhook_payload.json</span>
          </div>
          <div className={styles.codeBlock}>
            <WebhookPayload />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
