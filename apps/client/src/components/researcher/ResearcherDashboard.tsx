import { useState } from 'react';
import { Layout } from '../common/Layout';
import { SearchInput } from './SearchInput';
import { ResultsGrid } from './ResultsGrid';
import { useQuery } from '../../hooks/useQuery';

export const ResearcherDashboard = () => {
  const [query, setQuery] = useState('');
  const { results, isLoading, queryData } = useQuery();

  const handleSearch = () => {
    queryData(query);
  };

  return (
    <Layout title="Researcher Dashboard">
      <div className="space-y-6">
        <div className="text-center sm:text-left">
          <h2 className="text-xl sm:text-2xl font-semibold text-gray-900 mb-2">
            Query ARGO Data
          </h2>
          <p className="text-sm text-gray-600">
            Search and analyze ocean data from ARGO floats worldwide
          </p>
        </div>
        
        <SearchInput
          query={query}
          onQueryChange={setQuery}
          onSearch={handleSearch}
          isLoading={isLoading}
        />
        
        <ResultsGrid results={results} />
      </div>
    </Layout>
  );
};