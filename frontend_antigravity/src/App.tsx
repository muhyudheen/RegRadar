import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home/Home';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      {/* Future routes */}
      {/* <Route path="/features" element={<Features />} /> */}
      {/* <Route path="/pricing" element={<Pricing />} /> */}
      {/* <Route path="/dashboard/*" element={<Dashboard />} /> */}
      {/* <Route path="/playground" element={<Playground />} /> */}
    </Routes>
  );
}

export default App;
