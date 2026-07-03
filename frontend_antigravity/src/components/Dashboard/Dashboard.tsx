import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Radar, LayoutDashboard, Webhook, Activity, KeyRound, LogOut } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAuth } from '../../lib/AuthContext';
import AuthGate from './AuthGate';
import styles from './Dashboard.module.css';

const NAV_ITEMS = [
  { to: '/dashboard/overview', label: 'Overview', icon: LayoutDashboard },
  { to: '/dashboard/subscriptions', label: 'Subscriptions', icon: Webhook },
  { to: '/dashboard/feed', label: 'Change Feed', icon: Activity },
  { to: '/dashboard/keys', label: 'API Keys', icon: KeyRound },
];

function Shell() {
  const { logout, me, meError } = useAuth();
  const navigate = useNavigate();
  const [confirmLogout, setConfirmLogout] = useState(false);

  function handleLogout() {
    setConfirmLogout(false);
    logout();
    navigate('/login');
  }

  // loaded → capitalized tier; loading → "…"; error → "—" (never a raw object)
  const tierLabel = me
    ? me.tier.charAt(0).toUpperCase() + me.tier.slice(1)
    : meError
      ? '—'
      : '…';

  return (
    <div className={styles.root}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarTop}>
          <NavLink to="/" className={styles.brand} aria-label="Lawhook home">
            <Radar className={styles.brandIcon} />
            <span className={styles.brandText}>Lawhook</span>
          </NavLink>

          <nav className={styles.nav}>
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`
                }
              >
                <Icon size={16} className={styles.navIcon} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </aside>

      <div className={styles.main}>
        <header className={styles.topbar}>
          <div className={styles.topbarLeft}>
            <span className={styles.tierBadge} title={meError ?? undefined}>
              {tierLabel}
            </span>
          </div>
          <div className={styles.topbarRight}>
            <button
              type="button"
              className={styles.disconnect}
              onClick={() => setConfirmLogout(true)}
            >
              <LogOut size={14} />
              Log out
            </button>
          </div>
        </header>

        <main className={styles.content}>
          <Outlet />
        </main>
      </div>

      <AnimatePresence>
        {confirmLogout && (
          <motion.div
            key="confirm-logout"
            className={styles.overlay}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setConfirmLogout(false)}
          >
            <motion.div
              className={styles.confirmModal}
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.2 }}
            >
              <h3 className={styles.confirmTitle}>Log out?</h3>
              <p className={styles.confirmText}>
                Are you sure you want to log out? You’ll need to sign in again to
                access your dashboard.
              </p>
              <div className={styles.confirmActions}>
                <button
                  type="button"
                  className={styles.ghostBtn}
                  onClick={() => setConfirmLogout(false)}
                >
                  Cancel
                </button>
                <button type="button" className={styles.dangerBtn} onClick={handleLogout}>
                  <LogOut size={14} />
                  Log out
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Dashboard() {
  // AuthProvider lives at the app root (see App.tsx) so the public auth/
  // signup pages share the same in-memory JWT session.
  return (
    <AuthGate>
      <Shell />
    </AuthGate>
  );
}
