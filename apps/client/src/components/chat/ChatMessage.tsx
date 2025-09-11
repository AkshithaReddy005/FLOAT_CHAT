import React from 'react';
import { formatChatMessage } from '../../utils/formatChatMessage';
import { VisualizationCard } from './VisualizationCard';
import type { ChatResponse, ArgoMeasurement } from '../../types';

export interface ChatMessageProps {
  message: string;
  isUser: boolean;
  timestamp: Date;
  isTyping?: boolean;
  chatResponse?: ChatResponse;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isUser,
  timestamp,
  isTyping = false,
  chatResponse
}) => {
  // Convert data to ArgoMeasurement format for visualization
  const results: ArgoMeasurement[] = chatResponse?.data?.map((item: any, index: number) => ({
    float_id: String(item.float_id || item.id || `float_${index + 1}`),
    latitude: Number(item.latitude || 0),
    longitude: Number(item.longitude || 0),
    date: String(item.date || item.time || new Date().toISOString().split('T')[0]),
    depth: Number(item.depth || 0),
    temperature: Number(item.temperature || 0),
    salinity: Number(item.salinity || 0),
    pressure: Number(item.pressure || 0)
  })) || [];
  return (
    <div className={`flex w-full mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-[85%] sm:max-w-[75%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 ${isUser ? 'ml-3' : 'mr-3'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
            isUser 
              ? 'bg-blue-600 text-white' 
              : 'bg-gradient-to-br from-emerald-500 to-blue-600 text-white'
          }`}>
            {isUser ? 'U' : 'AI'}
          </div>
        </div>

        {/* Message Content */}
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          <div
            className={`px-4 py-3 rounded-2xl shadow-sm transition-all duration-300 ${
              isUser
                ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white'
                : 'bg-white text-gray-800 border border-gray-200 hover:shadow-md'
            } ${isTyping ? 'animate-pulse' : ''}`}
          >
            {isTyping ? (
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-xs text-gray-500">FloatChat is thinking...</span>
              </div>
            ) : (
              <div 
                className={`text-sm sm:text-base leading-relaxed ${isUser ? 'text-white' : 'text-gray-800'}`}
                dangerouslySetInnerHTML={{ 
                  __html: isUser ? message : formatChatMessage(message) 
                }} 
              />
            )}
          </div>
          
          {/* Timestamp */}
          <div className={`text-xs text-gray-500 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
            {timestamp.toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </div>

          {/* Visualization Card for AI messages with data */}
          {!isUser && !isTyping && chatResponse && (
            <VisualizationCard chatResponse={chatResponse} results={results} />
          )}
        </div>
      </div>
    </div>
  );
};