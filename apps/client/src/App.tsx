import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { LoginScreen } from './components/common/LoginScreen';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { ChatDashboard } from './components/researcher/ChatDashboard';
import { TestingDashboard } from './components/admin/TestingDashboard';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LoginScreen />} />
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
        <Route path="/user/chat" element={<ChatDashboard />} />
        <Route path="/admin/testing" element={<TestingDashboard />} />
      </Routes>
    </Router>
  );
}

export default App
