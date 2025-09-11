import React from 'react';

export const MessageLoadingSkeleton: React.FC = () => {
  return (
    <div className="flex w-full mb-4 justify-start">
      <div className="flex max-w-[85%] sm:max-w-[75%] flex-row">
        {/* Avatar Skeleton */}
        <div className="flex-shrink-0 mr-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-blue-600 animate-pulse"></div>
        </div>

        {/* Message Content Skeleton */}
        <div className="flex flex-col items-start">
          <div className="px-4 py-3 rounded-2xl bg-white border border-gray-200 shadow-sm">
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 rounded animate-pulse w-48"></div>
              <div className="h-4 bg-gray-200 rounded animate-pulse w-32"></div>
              <div className="h-4 bg-gray-200 rounded animate-pulse w-56"></div>
            </div>
          </div>
          
          {/* Timestamp Skeleton */}
          <div className="h-3 bg-gray-200 rounded animate-pulse w-16 mt-1"></div>
        </div>
      </div>
    </div>
  );
};