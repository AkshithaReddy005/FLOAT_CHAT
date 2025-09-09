import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { LoginScreen } from './components/common/LoginScreen';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { ResearcherDashboard } from './components/researcher/ResearcherDashboard';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LoginScreen />} />
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
        <Route path="/user/chat" element={<ResearcherDashboard />} />
      </Routes>
    </Router>
  );
}

export default App
