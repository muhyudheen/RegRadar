import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Logo from '../Logo/Logo';
import { motion, AnimatePresence } from 'framer-motion';
import styles from './Navbar.module.css';

/** Navigation link definition */
interface NavItem {
  label: string;
  to: string;
}

const NAV_LINKS: NavItem[] = [
  { label: 'Features', to: '/features' },
  { label: 'Pricing', to: '/pricing' },
  { label: 'Docs', to: '/docs' },
];

interface NavbarProps {
  /** When true, renders with a fully transparent background until the user scrolls. */
  transparent?: boolean;
}

/**
 * Fixed-position Navbar with glass-blur background.
 *
 * - Shows a subtle bottom border only after scrolling.
 * - Accepts a `transparent` prop for hero section overlay.
 * - Collapses into a hamburger menu below 768px.
 */
export default function Navbar({ transparent = false }: NavbarProps) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  /* ── Scroll listener to toggle bottom border ── */
  const handleScroll = useCallback(() => {
    setScrolled(window.scrollY > 10);
  }, []);

  useEffect(() => {
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // check initial position
    return () => window.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  /* Close mobile menu on route change (link click) */
  const closeMobile = () => setMobileOpen(false);

  /* Build class string */
  const navClasses = [
    styles.navbar,
    scrolled && styles.scrolled,
    transparent && styles.transparent,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <nav className={navClasses}>
      <div className={styles.inner}>
        {/* ── Logo ── */}
        <Link to="/" className={styles.logo} aria-label="Lawhook home">
          <Logo className={styles.logoIcon} />
          <span className={styles.logoText}>Lawhook</span>
        </Link>

        {/* ── Desktop links ── */}
        <div className={styles.navLinks}>
          {NAV_LINKS.map((item) => (
            <Link key={item.to} to={item.to} className={styles.navLink}>
              {item.label}
            </Link>
          ))}
        </div>

        {/* ── Right actions ── */}
        <div className={styles.actions}>
          <Link to="/get-started" className={`btn btn-primary ${styles.desktopCta}`}>
            Get API Key
          </Link>

          {/* Hamburger toggle (visible on mobile only) */}
          <button
            className={styles.hamburger}
            onClick={() => setMobileOpen((prev) => !prev)}
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* ── Mobile dropdown ── */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className={styles.mobileMenu}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
          >
            {NAV_LINKS.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={styles.mobileLink}
                onClick={closeMobile}
              >
                {item.label}
              </Link>
            ))}
            <Link
              to="/get-started"
              className={`btn btn-primary ${styles.mobileCta}`}
              onClick={closeMobile}
            >
              Get API Key
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
