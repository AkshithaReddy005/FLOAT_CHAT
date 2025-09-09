import { useNavigate } from 'react-router-dom';
import { Button } from './Button';

export const LoginScreen = () => {
  const navigate = useNavigate();

  const handleUserTypeSelect = (type: 'admin' | 'researcher') => {
    if (type === 'admin') {
      navigate('/admin/dashboard');
    } else {
      navigate('/user/chat');
    }
  };
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-100 via-slate-50 to-slate-50"></div>
      <div className="absolute top-20 left-20 w-32 h-32 bg-indigo-200 rounded-full opacity-30 blur-xl animate-pulse"></div>
      <div className="absolute bottom-20 right-20 w-24 h-24 bg-purple-200 rounded-full opacity-30 blur-xl animate-pulse" style={{animationDelay: '1s'}}></div>
      
      <div className="relative bg-white/80 backdrop-blur-sm rounded-3xl shadow-xl border border-indigo-100 p-6 sm:p-8 lg:p-12 w-full max-w-md mx-auto">
        <div className="text-center space-y-8">
          <div className="space-y-3">
            <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent leading-tight">
              FloatChat
            </h1>
            <p className="text-indigo-600 font-semibold text-lg">
              ARGO Data System
            </p>
            <p className="text-slate-600 text-sm leading-relaxed">
              Advanced ocean data analysis and research platform
            </p>
          </div>
          
          <div className="space-y-4">
            <p className="text-slate-700 font-medium">
              Choose your access level:
            </p>
            
            <div className="space-y-3">
              <Button 
                variant="admin"
                size="lg"
                onClick={() => handleUserTypeSelect('admin')}
                className="w-full"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.031 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                Admin Portal
              </Button>
              <Button 
                variant="researcher"
                size="lg"
                onClick={() => handleUserTypeSelect('researcher')}
                className="w-full"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Research Access
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};