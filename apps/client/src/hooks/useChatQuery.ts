import { useState } from 'react';
import { apiService } from '../services/api';
import type { ArgoMeasurement, ChatResponse } from '../types';

export const useChatQuery = () => {
  const [results, setResults] = useState<ArgoMeasurement[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');

  const chatWithContext = async (message: string, context?: any): Promise<ChatResponse | null> => {
    if (!message.trim()) return null;

    setIsLoading(true);
    setError('');
    
    try {
      console.log('Sending chat request:', { message, context });
      
      // Call the enhanced API with context
      const response = await apiService.chatWithContextData(message, context);
      console.log('Received response:', response);
      
      setResults(response.data || []);
      return response;
    } catch (error) {
      console.error('Chat query error:', error);
      
      // Provide helpful error messages
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
      
      setError(errorMessage);
      setResults([]);
      
      // Return error response
      return {
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
      };
    } finally {
      setIsLoading(false);
    }
  };

  return {
    results,
    isLoading,
    error,
    chatWithContext,
  };
};