import { useState } from 'react';
import { apiService } from '../services/api';
import type { ArgoMeasurement, ChatResponse } from '../types';

export const useQuery = () => {
  const [results, setResults] = useState<ArgoMeasurement[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string>('');
  const [chatResponse, setChatResponse] = useState<ChatResponse | null>(null);

  const queryData = async (query: string): Promise<void> => {
    if (!query.trim()) return;

    setIsLoading(true);
    try {
      const response = await apiService.chatWithData(query);
      setResults(response.data || []);
      setMessage(response.response);
      setChatResponse(response);
    } catch {
      setResults([]);
      setMessage('Query failed. Please try again.');
      setChatResponse(null);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    results,
    isLoading,
    message,
    chatResponse,
    queryData,
  };
};