import { Button } from '../common/Button';

interface SearchInputProps {
  query: string;
  onQueryChange: (query: string) => void;
  onSearch: () => void;
  isLoading: boolean;
}

export const SearchInput = ({ query, onQueryChange, onSearch, isLoading }: SearchInputProps) => {
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      onSearch();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoading) {
      onSearch();
    }
  };

  const suggestions = [
    "Show me recent data near Indian coast",
    "Temperature data from Arabian Sea 2024",
    "Salinity measurements in Bay of Bengal",
    "Deep water temperature profiles"
  ];

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <div className="text-center space-y-4">
        <div className="mx-auto w-16 h-16 bg-gradient-to-br from-indigo-500 to-blue-600 rounded-2xl flex items-center justify-center">
          <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-800 mb-2">
            Ocean Data Search
          </h2>
          <p className="text-slate-600">
            Ask questions about ARGO oceanographic data in natural language
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="w-full">
        <div className="relative">
          <label htmlFor="search-query" className="sr-only">
            Search query for ARGO data
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              id="search-query"
              type="text"
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="e.g., Show me recent temperature data near Indian coast"
              className="w-full pl-12 pr-32 py-4 text-sm sm:text-base bg-white border-2 border-slate-200 rounded-2xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-slate-50 disabled:text-slate-500 transition-all duration-300 shadow-lg hover:shadow-xl"
              disabled={isLoading}
              aria-describedby="search-help"
            />
            <div className="absolute inset-y-0 right-0 pr-2 flex items-center">
              <Button 
                type="submit"
                onClick={onSearch}
                disabled={isLoading || !query.trim()}
                variant="primary"
                size="md"
                loading={isLoading}
                className="px-6"
              >
                {isLoading ? 'Searching...' : 'Search'}
              </Button>
            </div>
          </div>
        </div>
        
        <div className="mt-4 space-y-3">
          <p className="text-sm text-slate-600 font-medium">
            Try these example queries:
          </p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                type="button"
                onClick={() => onQueryChange(suggestion)}
                disabled={isLoading}
                className="px-4 py-2 text-sm bg-indigo-50 text-indigo-700 rounded-xl hover:bg-indigo-100 transition-colors duration-200 border border-indigo-200 disabled:opacity-50"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </form>
    </div>
  );
};