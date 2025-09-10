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
    } catch (error) {
      console.error('Query error:', error);
      
      // Provide a more helpful error message based on the error type
      let errorMessage = '';
      
      if (error instanceof Error) {
        if (error.message.includes('Failed to fetch') || error.message.includes('Unable to connect')) {
          errorMessage = "I'm having trouble connecting to the server. Please check that the backend service is running and try again.";
        } else if (error.message.includes('500')) {
          errorMessage = "I encountered a server error while processing your query. This might be a temporary issue - please try rephrasing your question or asking about available data.";
        } else if (error.message.includes('timeout')) {
          errorMessage = "Your query is taking longer than expected to process. This might be due to a complex search - try asking about a smaller geographic area or time period.";
        } else {
          errorMessage = `I encountered an issue while processing your request: ${error.message}. You can try rephrasing your question or asking about what data is available.`;
        }
      } else {
        errorMessage = "I'm experiencing technical difficulties. Please try asking about available ARGO data, recent measurements, or specific ocean regions.";
      }
      
      // Still show an empty result set but with a helpful message
      setResults([]);
      setMessage(errorMessage);
      setChatResponse({
        response: errorMessage,
        data: [],
        visualization: {
          map: { 
            type: 'scatter',
            points: [] 
          },
          depth_profile: { 
            type: 'line',
            data: [] 
          }
        },
        query_params: {
          limit: 0
        },
        context_count: 0
      });
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