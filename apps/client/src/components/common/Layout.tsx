interface LayoutProps {
  children: React.ReactNode;
  title?: string;
}

export const Layout = ({ children, title }: LayoutProps) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 via-purple-600 to-blue-700 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-2xl shadow-2xl min-h-[80vh] p-4 sm:p-6 lg:p-8">
          {title && (
            <header className="mb-6 pb-4 border-b border-gray-200">
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 text-center">
                {title}
              </h1>
            </header>
          )}
          <main className="space-y-6" role="main" aria-label={title ? `${title} content` : "Main content"}>
            {children}
          </main>
        </div>
      </div>
    </div>
  );
};