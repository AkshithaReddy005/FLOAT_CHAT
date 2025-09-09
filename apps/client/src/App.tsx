import { useState } from 'react';
import { LoginScreen } from './components/common/LoginScreen';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { ResearcherDashboard } from './components/researcher/ResearcherDashboard';
import type { UserType } from './types';

function App() {
  const [userType, setUserType] = useState<UserType>(null);

  if (!userType) {
    return <LoginScreen onSelectUserType={setUserType} />;
  }

  if (userType === 'admin') {
    return <AdminDashboard />;
  }

  if (userType === 'researcher') {
    return <ResearcherDashboard />;
  }

  return null;
}

export default App
