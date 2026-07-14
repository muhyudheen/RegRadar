import { useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider } from './lib/AuthContext';
import Home from './pages/Home/Home';
import Pricing from './components/Pricing/Pricing';
import GetStarted from './pages/GetStarted/GetStarted';
import Quickstart from './pages/Quickstart/Quickstart';
import Auth from './pages/Auth/Auth';
import Dashboard from './components/Dashboard/Dashboard';
import ErrorBoundary from './components/Dashboard/ErrorBoundary';
import Overview from './components/Dashboard/Overview/Overview';
import Subscriptions from './components/Dashboard/Subscriptions/Subscriptions';
import ChangeFeed from './components/Dashboard/ChangeFeed/ChangeFeed';
import ApiKeys from './components/Dashboard/ApiKeys/ApiKeys';

/**
 * Smooth-scrolls to a `#hash` target after navigation. React Router doesn't
 * scroll to hashes itself, so links like `/#features` (even from another page)
 * only change the URL without this. Runs after render so the target exists.
 */
function ScrollToHash() {
  const { hash, pathname } = useLocation();

  useEffect(() => {
    if (!hash) return;
    const id = hash.slice(1);
    const timer = window.setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 0);
    return () => window.clearTimeout(timer);
  }, [hash, pathname]);

  return null;
}

function App() {
  return (
    // Shared in-memory JWT session — spans the public auth/signup pages and the
    // gated dashboard, so signup can hand straight into the dashboard.
    <AuthProvider>
      <ScrollToHash />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/docs" element={<Quickstart />} />
        <Route path="/get-started" element={<GetStarted />} />
        <Route path="/login" element={<Auth mode="login" />} />
        <Route path="/signup" element={<Auth mode="signup" />} />

        <Route
          path="/dashboard"
          element={
            <ErrorBoundary>
              <Dashboard />
            </ErrorBoundary>
          }
        >
          <Route index element={<Navigate to="subscriptions" replace />} />
          <Route path="overview" element={<Overview />} />
          <Route path="subscriptions" element={<Subscriptions />} />
          <Route path="feed" element={<ChangeFeed />} />
          <Route path="keys" element={<ApiKeys />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}

export default App;
