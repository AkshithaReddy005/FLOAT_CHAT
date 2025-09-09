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
    <Layout title="Research Portal">
      <div className="space-y-8">
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