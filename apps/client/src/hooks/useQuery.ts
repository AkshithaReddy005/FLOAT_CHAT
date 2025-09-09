import { useState } from 'react';
import { apiService } from '../services/api';
import type { ArgoMeasurement } from '../types';

export const useQuery = () => {
  const [results, setResults] = useState<ArgoMeasurement[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string>('');

  const queryData = async (query: string): Promise<void> => {
    if (!query.trim()) return;

    setIsLoading(true);
    try {
      const response = await apiService.queryData(query);
      setResults(response.results || []);
      setMessage(response.message);
    } catch {
      setResults([]);
      setMessage('Query failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return {
    results,
    isLoading,
    message,
    queryData,
  };
};