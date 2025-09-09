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

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
        <div className="flex-1">
          <label htmlFor="search-query" className="sr-only">
            Search query for ARGO data
          </label>
          <input
            id="search-query"
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="e.g., Show me recent data near Indian coast"
            className="w-full px-4 py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-50 disabled:text-gray-500 transition-colors"
            disabled={isLoading}
            aria-describedby="search-help"
          />
          <p id="search-help" className="mt-1 text-xs text-gray-500">
            Use natural language to query oceanographic data
          </p>
        </div>
        
        <Button 
          type="submit"
          onClick={onSearch}
          disabled={isLoading || !query.trim()}
          variant="search"
          className="sm:self-start"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Searching...
            </>
          ) : (
            'Search'
          )}
        </Button>
      </div>
    </form>
  );
};