import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './lib/AuthContext';
import Home from './pages/Home/Home';
import Pricing from './components/Pricing/Pricing';
import GetStarted from './pages/GetStarted/GetStarted';
import Auth from './pages/Auth/Auth';
import Dashboard from './components/Dashboard/Dashboard';
import ErrorBoundary from './components/Dashboard/ErrorBoundary';
import Overview from './components/Dashboard/Overview/Overview';
import Subscriptions from './components/Dashboard/Subscriptions/Subscriptions';
import ChangeFeed from './components/Dashboard/ChangeFeed/ChangeFeed';
import ApiKeys from './components/Dashboard/ApiKeys/ApiKeys';

function App() {
  return (
    // Shared in-memory JWT session — spans the public auth/signup pages and the
    // gated dashboard, so signup can hand straight into the dashboard.
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/pricing" element={<Pricing />} />
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
