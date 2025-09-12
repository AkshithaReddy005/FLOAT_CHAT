import React, { useRef, useCallback } from 'react';
import { Layout } from '../common/Layout';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { ChatInterface, type ChatInterfaceRef } from '../chat/ChatInterface';
import { useChatQuery } from '../../hooks/useChatQuery';
import type { ChatResponse } from '../../types';

interface APIContext {
  recent_exchanges: Array<{
    user_query: string;
    ai_response_summary: string;
    timestamp: string;
  }>;
  key_context: {
    locations: string[];
    time_ranges: string[];
    data_types: string[];
    recent_focus: string[];
  };
  conversation_summary: string;
}

export const ChatDashboard: React.FC = () => {
  const chatInterfaceRef = useRef<ChatInterfaceRef>(null);
  const {isLoading, error, chatWithContext } = useChatQuery();

  // Handle sending messages to the API
  const handleSendMessage = useCallback(async (message: string, context?: APIContext) => {
    try {
      const response = await chatWithContext(message, context);
      if (response && chatInterfaceRef.current) {
        chatInterfaceRef.current.handleApiResponse(response);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      // Error handling is done in useChatQuery hook
    }
  }, [chatWithContext]);

  // Handle responses for any additional processing if needed
  const handleResponse = useCallback((response: ChatResponse) => {
    // Additional response handling can go here if needed in the future
    console.log('Response received:', response);
  }, []);

  return (
    <ErrorBoundary>
      <Layout title="">
        <div className="h-full flex flex-col bg-gray-50">
          {/* Main Chat Interface */}
          <div className="flex-1 flex flex-col min-h-0">
            <ErrorBoundary fallback={
              <div className="flex items-center justify-center h-full">
                <div className="text-center p-8">
                  <h3 className="text-lg font-semibold text-gray-800 mb-2">Chat Interface Error</h3>
                  <p className="text-gray-600">Please refresh the page to continue</p>
                </div>
              </div>
            }>
              <ChatInterface
                ref={chatInterfaceRef}
                onResponse={handleResponse}
                isLoading={isLoading}
                onSendMessage={handleSendMessage}
              />
            </ErrorBoundary>
          </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4 mx-4 mb-4 rounded-r-lg">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}
        </div>
      </Layout>
    </ErrorBoundary>
  );
};