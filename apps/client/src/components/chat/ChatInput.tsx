import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = "Type your message..."
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative flex items-end gap-3 p-3 bg-white border border-gray-200 rounded-2xl shadow-sm hover:shadow-md focus-within:shadow-lg focus-within:ring-2 focus-within:ring-blue-500/20 transition-all duration-300">
        {/* Text Input */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={`
              w-full px-0 py-1 
              bg-transparent border-none outline-none resize-none
              disabled:text-gray-500
              text-sm sm:text-base
              placeholder-gray-400
              ${disabled ? 'cursor-not-allowed' : ''}
            `}
            style={{
              minHeight: '24px',
              maxHeight: '96px'
            }}
          />
          
          {/* Character count for very long messages */}
          {message.length > 500 && (
            <div className="absolute bottom-1 right-2 text-xs text-gray-400">
              {message.length}/2000
            </div>
          )}
        </div>

        {/* Send Button */}
        <button
          type="submit"
          disabled={disabled || !message.trim()}
          className={`
            flex-shrink-0 w-9 h-9 
            rounded-lg flex items-center justify-center
            transition-all duration-200
            ${
              disabled || !message.trim()
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 hover:scale-105 active:scale-95'
            }
          `}
        >
          {disabled ? (
            <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Input hints */}
      <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
        <span>
          Press Enter to send, Shift+Enter for new line
        </span>
        {disabled && (
          <span className="text-blue-600 flex items-center">
            <div className="w-3 h-3 border border-blue-600 border-t-transparent rounded-full animate-spin mr-1" />
            Processing...
          </span>
        )}
      </div>
    </form>
  );
};