interface ButtonProps {
  onClick: () => void;
  disabled?: boolean;
  variant?: 'admin' | 'researcher' | 'search';
  children: React.ReactNode;
  className?: string;
  type?: 'button' | 'submit' | 'reset';
}

export const Button = ({ 
  onClick, 
  disabled = false, 
  variant = 'search', 
  children, 
  className = '',
  type = 'button'
}: ButtonProps) => {
  const getButtonClass = () => {
    const baseClass = 'px-4 py-3 sm:px-6 sm:py-3 font-semibold text-sm sm:text-base rounded-lg transition-all duration-200 focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
    
    switch (variant) {
      case 'admin':
        return `${baseClass} bg-red-600 hover:bg-red-700 text-white focus:ring-red-500 active:bg-red-800`;
      case 'researcher':
        return `${baseClass} bg-blue-600 hover:bg-blue-700 text-white focus:ring-blue-500 active:bg-blue-800`;
      case 'search':
        return `${baseClass} bg-blue-600 hover:bg-blue-700 text-white focus:ring-blue-500 active:bg-blue-800 whitespace-nowrap`;
      default:
        return `${baseClass} bg-gray-600 hover:bg-gray-700 text-white focus:ring-gray-500`;
    }
  };

  return (
    <button 
      type={type}
      className={`${getButtonClass()} ${className}`}
      onClick={onClick}
      disabled={disabled}
      aria-disabled={disabled}
    >
      {children}
    </button>
  );
};