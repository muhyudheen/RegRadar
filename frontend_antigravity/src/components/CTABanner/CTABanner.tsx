import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import styles from './CTABanner.module.css';

function CTABanner() {
  const ref = useRef<HTMLElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section ref={ref} className={styles.root}>
      <div className={styles.glow} />

      <motion.div
        className={styles.content}
        initial={{ opacity: 0, y: 24 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] as const }}
      >
        <h2 className={styles.headline}>
          Built for compliance teams.
          <br />
          Ready in five minutes.
        </h2>

        <p className={styles.sub}>
          Free tier includes 1 subscription · 1,000 requests/day · no credit
          card required.
        </p>

        <Link to="/get-started" className={`btn btn-primary btn-lg ${styles.cta}`}>
          Get Your API Key
          <ArrowRight size={16} />
        </Link>
      </motion.div>
    </section>
  );
}

export default CTABanner;
