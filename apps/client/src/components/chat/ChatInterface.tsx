import React, { useState, useRef, useEffect } from 'react';
import { Trash2, Waves } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { SessionContextManager } from '../../services/sessionContext';
import type { ChatResponse } from '../../types';

export interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  chatResponse?: ChatResponse;
}

interface ChatInterfaceProps {
  onResponse: (response: ChatResponse) => void;
  isLoading: boolean;
  onSendMessage: (message: string, context?: any) => Promise<void>;
}

export interface ChatInterfaceRef {
  handleApiResponse: (response: ChatResponse) => void;
}

export const ChatInterface = React.forwardRef<ChatInterfaceRef, ChatInterfaceProps>(({
  onResponse,
  isLoading,
  onSendMessage
}, ref) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [showTyping, setShowTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionManager = useRef(new SessionContextManager());

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, showTyping]);

  // Load existing messages from session on mount
  useEffect(() => {
    const savedMessages = sessionManager.current.getMessages();
    if (savedMessages.length > 0) {
      setMessages(savedMessages);
    }
  }, []);

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Add user message immediately
    const userMessage: Message = {
      id: Date.now().toString(),
      content: content.trim(),
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setShowTyping(true);

    try {
      // Get session context for API call
      const context = sessionManager.current.getContextForAPI();
      
      // Store user message in session
      sessionManager.current.addMessage(userMessage);
      
      // Call API with context
      await onSendMessage(content.trim(), context);
      
      setShowTyping(false);
    } catch (error) {
      console.error('Error sending message:', error);
      setShowTyping(false);
      
      // Add error message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "I'm sorry, I encountered an error while processing your request. Please try again.",
        isUser: false,
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
      sessionManager.current.addMessage(errorMessage);
    }
  };

  // Handle API response - expose this method to parent
  const handleApiResponse = React.useCallback((response: ChatResponse) => {
    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: response.response,
      isUser: false,
      timestamp: new Date(),
      chatResponse: response
    };

    setMessages(prev => [...prev, aiMessage]);
    sessionManager.current.addMessage(aiMessage);
    setShowTyping(false);
    onResponse(response);
  }, [onResponse]);

  // Expose handleApiResponse to parent component
  React.useImperativeHandle(ref, () => ({
    handleApiResponse
  }));

  // Effect to handle response updates from parent
  useEffect(() => {
    if (!isLoading && showTyping) {
      setShowTyping(false);
    }
  }, [isLoading, showTyping]);

  const clearConversation = () => {
    setMessages([]);
    sessionManager.current.clearSession();
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4 sm:px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-xl flex items-center justify-center">
              <Waves className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">FloatChat</h2>
              <p className="text-sm text-gray-500">Your intelligent ocean data companion</p>
            </div>
          </div>
          
          {messages.length > 0 && (
            <button
              onClick={clearConversation}
              className="flex items-center space-x-1 text-sm text-gray-500 hover:text-gray-700 px-3 py-1 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <h3 className="text-xl font-semibold text-gray-800 mb-2">
              Dive into <span className="bg-gradient-to-r from-blue-500 to-cyan-600 bg-clip-text text-transparent">Ocean Intelligence</span>
            </h3>
            <p className="text-gray-600 mb-6 max-w-md">
              Explore vast oceanographic datasets with AI-powered insights. Ask questions about temperature patterns, salinity levels, or discover hidden trends in marine data.
            </p>
            <div className="flex flex-wrap gap-2 justify-center max-w-2xl">
              {[
                "What's the current temperature near Mumbai?",
                "Show salinity trends in Arabian Sea",
                "Find anomalies in Bay of Bengal data",
                "Deep water analysis for research"
              ].map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSendMessage(suggestion)}
                  className="px-4 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg border border-blue-200 hover:bg-blue-100 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message.content}
                isUser={message.isUser}
                timestamp={message.timestamp}
                chatResponse={message.chatResponse}
              />
            ))}
            
            {showTyping && (
              <ChatMessage
                message=""
                isUser={false}
                timestamp={new Date()}
                isTyping={true}
              />
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 bg-white border-t border-gray-200 px-4 sm:px-6 py-4">
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={isLoading}
          placeholder="Explore ocean data - ask about temperatures, trends, or locations..."
        />
      </div>
    </div>
  );
});