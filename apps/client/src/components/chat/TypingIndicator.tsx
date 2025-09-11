import React from 'react';

export const TypingIndicator: React.FC = () => {
  return (
    <div className="flex items-center space-x-2 px-4 py-3 bg-white rounded-2xl border border-gray-200 shadow-sm max-w-20">
      <div className="flex space-x-1">
        <div 
          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
          style={{ animationDelay: '0ms' }}
        ></div>
        <div 
          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
          style={{ animationDelay: '150ms' }}
        ></div>
        <div 
          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
          style={{ animationDelay: '300ms' }}
        ></div>
      </div>
      <span className="text-xs text-gray-500">Thinking...</span>
    </div>
  );
};