import styles from './SocialProof.module.css';

const COMPANIES = [
  { name: 'Meridian', style: 'normal' as const },
  { name: 'CLEARWAY', style: 'caps' as const },
  { name: 'NexusAI', style: 'normal' as const },
  { name: 'Sentinel', style: 'normal' as const },
  { name: 'APEX', style: 'caps' as const },
  { name: 'QuantumLedger', style: 'normal' as const },
];

export default function SocialProof() {
  const logos = COMPANIES.map((c) => (
    <span
      key={c.name}
      className={`${styles.logo} ${c.style === 'caps' ? styles.logoCaps : ''}`}
    >
      {c.name}
    </span>
  ));

  return (
    <section className={styles.root}>
      <div className={styles.logoRow}>{logos}</div>

      {/* Mobile marquee */}
      <div className={styles.marqueeWrapper}>
        <div className={styles.marqueeTrack}>
          {logos}
          {logos}
        </div>
      </div>
    </section>
  );
}
