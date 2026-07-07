import { useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Check } from 'lucide-react';
import { Link } from 'react-router-dom';
import Navbar from '../Navbar/Navbar';
import Footer from '../Footer/Footer';
import CTABanner from '../CTABanner/CTABanner';
import styles from './Pricing.module.css';

type Billing = 'monthly' | 'annual';

interface Tier {
  name: string;
  descriptor: string;
  monthly: number | null;
  annual: number | null;
  subscriptions: string;
  polling: string;
  rateLimit: string;
  support: string;
  sla: string;
  webhook: string;
  features: string[];
  cta: string;
  ctaTo: string;
  popular?: boolean;
}

const TIERS: Tier[] = [
  {
    name: 'Free',
    descriptor: 'Explore regulatory monitoring',
    monthly: 0,
    annual: 0,
    subscriptions: '1',
    polling: 'Daily',
    rateLimit: '60/min · 1k/day',
    support: 'Community',
    sla: '—',
    webhook: 'Standard',
    features: [
      '60 req/min · 1k req/day',
      'All 4 jurisdictions',
      'Webhook delivery',
      'Community support',
    ],
    cta: 'Get started',
    ctaTo: '/get-started',
  },
  {
    name: 'Starter',
    descriptor: 'For teams starting automation',
    monthly: 49,
    annual: 490,
    subscriptions: '10',
    polling: 'Hourly',
    rateLimit: '600/min · 50k/day',
    support: 'Email',
    sla: '—',
    webhook: 'Standard',
    features: [
      '600 req/min · 50k req/day',
      'All 4 jurisdictions',
      'Webhook delivery',
      'Email support',
    ],
    cta: 'Start free trial',
    ctaTo: '/get-started',
  },
  {
    name: 'Pro',
    descriptor: 'Real-time regulatory intelligence',
    monthly: 199,
    annual: 1990,
    subscriptions: 'Unlimited',
    polling: 'Near real-time',
    rateLimit: '6,000/min · 1M/day',
    support: 'Priority',
    sla: '99.9%',
    webhook: 'Priority',
    features: [
      '6,000 req/min · 1M req/day',
      'All 4 jurisdictions',
      'Priority webhook delivery',
      'Priority support',
      '99.9% uptime SLA',
    ],
    cta: 'Start free trial',
    ctaTo: '/get-started',
    popular: true,
  },
  {
    name: 'Enterprise',
    descriptor: 'Custom regulatory infrastructure',
    monthly: null,
    annual: null,
    subscriptions: 'Unlimited',
    polling: 'Real-time',
    rateLimit: 'Custom',
    support: 'SLA + dedicated',
    sla: 'Custom',
    webhook: 'Dedicated',
    features: [
      'Custom rate limits',
      'All 4 jurisdictions',
      'Dedicated webhook delivery',
      'SLA + dedicated support',
      'Custom uptime SLA',
    ],
    cta: 'Contact us',
    ctaTo: '/contact',
  },
];

const COMPARISON_ROWS = [
  { label: 'Subscriptions', values: ['1', '10', 'Unlimited', 'Unlimited'] },
  { label: 'Polling frequency', values: ['Daily', 'Hourly', 'Near real-time', 'Real-time'] },
  { label: 'Jurisdictions', values: ['IN · US · SG · AU', 'IN · US · SG · AU', 'IN · US · SG · AU', 'IN · US · SG · AU'] },
  { label: 'Webhook delivery', values: ['Standard', 'Standard', 'Priority', 'Dedicated'] },
  { label: 'Rate limit', values: ['60/min · 1k/day', '600/min · 50k/day', '6,000/min · 1M/day', 'Custom'] },
  { label: 'Support level', values: ['Community', 'Email', 'Priority', 'SLA + dedicated'] },
  { label: 'SLA', values: ['—', '—', '99.9%', 'Custom'] },
];

function formatPrice(price: number | null): string {
  if (price === null) return 'Custom';
  if (price === 0) return '$0';
  return `$${price.toLocaleString()}`;
}

function PricingCard({ tier, billing, index }: { tier: Tier; billing: Billing; index: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  const price = billing === 'monthly' ? tier.monthly : tier.annual;
  const period = price === null || price === 0 ? '' : billing === 'monthly' ? '/mo' : '/yr';

  return (
    <motion.div
      ref={ref}
      className={`${styles.card} ${tier.popular ? styles.cardPopular : ''}`}
      initial={{ opacity: 0, y: 32 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: 0.08 * index, ease: [0.4, 0, 0.2, 1] }}
    >
      {tier.popular && <span className={styles.popularBadge}>Most popular</span>}

      <h3 className={styles.tierName}>{tier.name}</h3>

      <div className={styles.priceRow}>
        <span className={styles.price}>{formatPrice(price)}</span>
        {period && <span className={styles.period}>{period}</span>}
      </div>

      <p className={styles.descriptor}>{tier.descriptor}</p>

      <div className={styles.differentiators}>
        <div className={styles.diffItem}>
          <span className={styles.diffValue}>{tier.subscriptions}</span>
          <span className={styles.diffLabel}>Subscriptions</span>
        </div>
        <div className={styles.diffItem}>
          <span className={styles.diffValue}>{tier.polling}</span>
          <span className={styles.diffLabel}>Polling</span>
        </div>
      </div>

      <div className={styles.divider} />

      <ul className={styles.featureList}>
        {tier.features.map((f) => (
          <li key={f} className={styles.featureItem}>
            <Check size={14} className={styles.checkIcon} />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      <Link
        to={tier.ctaTo}
        className={`${styles.ctaButton} ${tier.popular ? styles.ctaPrimary : styles.ctaGhost}`}
      >
        {tier.cta}
      </Link>
    </motion.div>
  );
}

export default function Pricing() {
  const [billing, setBilling] = useState<Billing>('monthly');

  const headerRef = useRef<HTMLDivElement>(null);
  const headerInView = useInView(headerRef, { once: true, margin: '-40px' });

  const tableRef = useRef<HTMLElement>(null);
  const tableInView = useInView(tableRef, { once: true, margin: '-80px' });

  return (
    <>
      <Navbar />
      <main>
        <section className={styles.header}>
          <motion.div
            ref={headerRef}
            className={styles.headerContent}
            initial={{ opacity: 0, y: 24 }}
            animate={headerInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
          >
            <h1 className={styles.headline}>Simple, transparent pricing</h1>
            <p className={styles.subheadline}>
              Start free. Scale as your compliance needs grow.
            </p>

            <div className={styles.toggleWrapper}>
              <div className={styles.toggle}>
                <button
                  className={`${styles.toggleOption} ${billing === 'monthly' ? styles.toggleActive : ''}`}
                  onClick={() => setBilling('monthly')}
                >
                  Monthly
                </button>
                <button
                  className={`${styles.toggleOption} ${billing === 'annual' ? styles.toggleActive : ''}`}
                  onClick={() => setBilling('annual')}
                >
                  Annual
                </button>
              </div>
              <span className={styles.saveBadge}>Save 2 months</span>
            </div>
          </motion.div>
        </section>

        <section className={styles.cardsSection}>
          <div className={styles.cardsGrid}>
            {TIERS.map((tier, i) => (
              <PricingCard key={tier.name} tier={tier} billing={billing} index={i} />
            ))}
          </div>
        </section>

        <section ref={tableRef} className={styles.tableSection}>
          <motion.div
            className={styles.tableContainer}
            initial={{ opacity: 0, y: 24 }}
            animate={tableInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
          >
            <h2 className={styles.tableHeadline}>Compare plans</h2>

            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.thFeature}>Feature</th>
                    {TIERS.map((t) => (
                      <th
                        key={t.name}
                        className={`${styles.thTier} ${t.popular ? styles.thPopular : ''}`}
                      >
                        {t.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {COMPARISON_ROWS.map((row) => (
                    <tr key={row.label}>
                      <td className={styles.tdFeature}>{row.label}</td>
                      {row.values.map((val, i) => (
                        <td
                          key={i}
                          className={`${styles.tdValue} ${TIERS[i].popular ? styles.tdPopular : ''}`}
                        >
                          {val}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className={styles.coverageCallout}>
              4 jurisdictions live — India, US, Singapore, Australia. More coming.
            </p>
          </motion.div>
        </section>

        <CTABanner />
      </main>
      <Footer />
    </>
  );
}
