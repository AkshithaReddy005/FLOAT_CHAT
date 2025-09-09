import { ResultCard } from './ResultCard';
import type { ArgoMeasurement } from '../../types';

interface ResultsGridProps {
  results: ArgoMeasurement[];
}

export const ResultsGrid = ({ results }: ResultsGridProps) => {
  if (results.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg sm:text-xl font-semibold text-gray-900">
          Search Results
        </h3>
        <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
          {results.length} result{results.length !== 1 ? 's' : ''}
        </span>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-6">
        {results.map((result, index) => (
          <ResultCard key={index} result={result} />
        ))}
      </div>
    </div>
  );
};