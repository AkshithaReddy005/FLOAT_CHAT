interface ButtonProps {
  onClick: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'admin' | 'researcher' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  className?: string;
  type?: 'button' | 'submit' | 'reset';
  loading?: boolean;
}

export const Button = ({ 
  onClick, 
  disabled = false, 
  variant = 'primary', 
  size = 'md',
  children, 
  className = '',
  type = 'button',
  loading = false
}: ButtonProps) => {
  const getButtonClass = () => {
    const baseClass = 'font-semibold rounded-xl transition-all duration-300 focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2';
    
    const sizeClasses = {
      sm: 'px-3 py-2 text-sm',
      md: 'px-4 py-3 sm:px-6 sm:py-3 text-sm sm:text-base',
      lg: 'px-6 py-4 sm:px-8 sm:py-4 text-base sm:text-lg'
    };
    
    const variantClasses = {
      primary: 'bg-indigo-600 hover:bg-indigo-700 text-white focus:ring-indigo-500 shadow-lg shadow-indigo-200',
      secondary: 'bg-indigo-50 hover:bg-indigo-100 text-indigo-700 focus:ring-indigo-500 border-2 border-indigo-200',
      admin: 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white focus:ring-indigo-500 shadow-lg shadow-indigo-200',
      researcher: 'bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white focus:ring-indigo-500 shadow-lg shadow-blue-200',
      danger: 'bg-rose-600 hover:bg-rose-700 text-white focus:ring-rose-500 shadow-lg shadow-rose-200',
      success: 'bg-emerald-600 hover:bg-emerald-700 text-white focus:ring-emerald-500 shadow-lg shadow-emerald-200'
    };
    
    return `${baseClass} ${sizeClasses[size]} ${variantClasses[variant]}`;
  };

  return (
    <button 
      type={type}
      className={`${getButtonClass()} ${className}`}
      onClick={onClick}
      disabled={disabled || loading}
      aria-disabled={disabled || loading}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      )}
      {children}
    </button>
  );
};