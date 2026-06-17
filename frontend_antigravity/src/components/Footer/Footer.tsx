import { Link } from 'react-router-dom';
import { Radar } from 'lucide-react';
import styles from './Footer.module.css';

/** Single footer link definition */
interface FooterLink {
  label: string;
  to: string;
}

/** Column of links */
interface FooterColumn {
  heading: string;
  links: FooterLink[];
}

const COLUMNS: FooterColumn[] = [
  {
    heading: 'Product',
    links: [
      { label: 'Features', to: '/features' },
      { label: 'Pricing', to: '/pricing' },
      { label: 'Changelog', to: '/changelog' },
      { label: 'Status', to: '/status' },
    ],
  },
  {
    heading: 'Developers',
    links: [
      { label: 'Documentation', to: '/docs' },
      { label: 'API Reference', to: '/docs/api' },
      { label: 'SDKs', to: '/docs/sdks' },
      { label: 'Playground', to: '/playground' },
    ],
  },
  {
    heading: 'Company',
    links: [
      { label: 'About', to: '/about' },
      { label: 'Blog', to: '/blog' },
      { label: 'Contact', to: '/contact' },
      { label: 'Careers', to: '/careers' },
    ],
  },
];

/**
 * Site-wide Footer with a 4-column layout:
 * Brand + description | Product | Developers | Company
 *
 * Responsive: collapses to 2 columns on tablet, 1 column on mobile.
 */
export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        {/* ── Main grid ── */}
        <div className={styles.grid}>
          {/* Brand column */}
          <div className={styles.brand}>
            <Link to="/" className={styles.logo} aria-label="Lawhook home">
              <Radar className={styles.logoIcon} />
              <span className={styles.logoText}>Lawhook</span>
            </Link>
            <p className={styles.brandDesc}>
              Regulatory change monitoring API for developers.
            </p>
          </div>

          {/* Link columns */}
          {COLUMNS.map((col) => (
            <div key={col.heading} className={styles.column}>
              <h4 className={styles.columnHeading}>{col.heading}</h4>
              <nav className={styles.columnLinks}>
                {col.links.map((link) => (
                  <Link key={link.to} to={link.to} className={styles.columnLink}>
                    {link.label}
                  </Link>
                ))}
              </nav>
            </div>
          ))}
        </div>

        {/* ── Bottom bar ── */}
        <div className={styles.bottom}>
          <span className={styles.copyright}>© 2026 Lawhook</span>
          <div className={styles.legal}>
            <Link to="/privacy" className={styles.legalLink}>
              Privacy
            </Link>
            <span className={styles.legalSep}>·</span>
            <Link to="/terms" className={styles.legalLink}>
              Terms
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
