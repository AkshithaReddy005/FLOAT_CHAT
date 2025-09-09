import { Button } from './Button';

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
  showBackButton?: boolean;
  onBack?: () => void;
}

export const Layout = ({ children, title, showBackButton = false, onBack }: LayoutProps) => {
  return (
    <div className="min-h-screen bg-slate-50 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-100 via-slate-50 to-slate-50"></div>
      <div className="absolute top-10 right-10 w-40 h-40 bg-indigo-200 rounded-full opacity-20 blur-2xl animate-pulse"></div>
      <div className="absolute bottom-10 left-10 w-32 h-32 bg-purple-200 rounded-full opacity-20 blur-2xl animate-pulse" style={{animationDelay: '2s'}}></div>
      
      <div className="relative p-4 sm:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-white/70 backdrop-blur-sm rounded-3xl shadow-xl border border-white/20 min-h-[85vh] p-6 sm:p-8 lg:p-12">
            {title && (
              <header className="mb-8 text-center">
                {showBackButton && (
                  <div className="flex justify-start mb-4">
                    <Button
                      onClick={onBack || (() => window.history.back())}
                      variant="secondary"
                      size="sm"
                      className="flex items-center gap-2"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                      Back
                    </Button>
                  </div>
                )}
                
                <div className="space-y-2">
                  <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent leading-tight">
                    {title}
                  </h1>
                  <div className="w-20 h-1 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full mx-auto"></div>
                </div>
              </header>
            )}
            
            <main 
              className="space-y-8" 
              role="main" 
              aria-label={title ? `${title} content` : "Main content"}
            >
              {children}
            </main>
          </div>
        </div>
      </div>
    </div>
  );
};