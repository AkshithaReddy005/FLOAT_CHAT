import React, { useState, useRef, useCallback } from 'react';
import { Layout } from '../common/Layout';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { ChatInterface, type ChatInterfaceRef } from '../chat/ChatInterface';
import { useChatQuery } from '../../hooks/useChatQuery';
import type { ChatResponse } from '../../types';

export const ChatDashboard: React.FC = () => {
  const chatInterfaceRef = useRef<ChatInterfaceRef>(null);
  const { results, isLoading, error, chatWithContext } = useChatQuery();
  const [currentResponse, setCurrentResponse] = useState<ChatResponse | null>(null);

  // Handle sending messages to the API
  const handleSendMessage = useCallback(async (message: string, context?: any) => {
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
    setCurrentResponse(response);
    // Additional response handling can go here
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

        {/* Status Bar (optional, for development) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="bg-gray-100 px-4 py-2 border-t text-xs text-gray-600">
            <div className="flex items-center justify-between">
              <span>
                Results: {results.length} | 
                Status: {isLoading ? 'Loading...' : 'Ready'} |
                Response: {currentResponse ? 'Received' : 'None'}
              </span>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isLoading ? 'bg-yellow-400' : 'bg-green-400'}`}></div>
                <span>Chat System</span>
              </div>
            </div>
          </div>
        )}
        </div>
      </Layout>
    </ErrorBoundary>
  );
};