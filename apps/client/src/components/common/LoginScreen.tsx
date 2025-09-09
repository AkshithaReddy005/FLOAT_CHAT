import { Button } from './Button';
import type { UserType } from '../../types';

interface LoginScreenProps {
  onSelectUserType: (type: UserType) => void;
}

export const LoginScreen = ({ onSelectUserType }: LoginScreenProps) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 via-purple-600 to-blue-700 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-6 sm:p-8 lg:p-12 w-full max-w-md mx-auto">
        <div className="text-center space-y-6">
          <div className="space-y-2">
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 leading-tight">
              FloatChat
            </h1>
            <p className="text-sm sm:text-base text-gray-600 font-medium">
              ARGO Data System
            </p>
          </div>
          
          <p className="text-gray-700 text-sm sm:text-base">
            Select your role to continue:
          </p>
          
          <div className="space-y-3 sm:space-y-4">
            <Button 
              variant="admin"
              onClick={() => onSelectUserType('admin')}
              className="w-full"
            >
              Login as Admin
            </Button>
            <Button 
              variant="researcher"
              onClick={() => onSelectUserType('researcher')}
              className="w-full"
            >
              Login as Researcher
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};