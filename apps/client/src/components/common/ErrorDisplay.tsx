interface ErrorDisplayProps {
  error: string | null;
  type?: 'error' | 'warning' | 'info';
  onDismiss?: () => void;
  className?: string;
}

const getErrorDetails = (error: string) => {
  const errorLower = error.toLowerCase();
  
  // File format errors
  if (errorLower.includes('not a netcdf') || errorLower.includes('invalid netcdf')) {
    return {
      title: 'Invalid File Format',
      message: 'Please upload a valid NetCDF file (.nc or .netcdf). Other file formats are not supported.',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      suggestions: [
        'Ensure your file has a .nc or .netcdf extension',
        'Verify the file was exported correctly from your data source',
        'Try re-downloading the file if it was corrupted during transfer'
      ]
    };
  }

  // ARGO attributes missing
  if (errorLower.includes('argo') && (errorLower.includes('attribute') || errorLower.includes('missing'))) {
    return {
      title: 'Missing ARGO Attributes',
      message: 'This NetCDF file does not contain the required ARGO ocean data attributes.',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      suggestions: [
        'Ensure your file is from an ARGO float measurement system',
        'Check that required variables like PRES, TEMP, PSAL are present',
        'Verify the file follows ARGO NetCDF conventions'
      ]
    };
  }

  // File size errors
  if (errorLower.includes('too large') || errorLower.includes('file size')) {
    return {
      title: 'File Size Exceeded',
      message: 'The uploaded file exceeds the maximum size limit of 50MB.',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      suggestions: [
        'Try compressing your NetCDF file using nccopy or similar tools',
        'Consider splitting large datasets into smaller files',
        'Contact support for assistance with large dataset uploads'
      ]
    };
  }

  // Network/server errors
  if (errorLower.includes('network') || errorLower.includes('connection') || errorLower.includes('server')) {
    return {
      title: 'Connection Error',
      message: 'Unable to connect to the server. Please check your internet connection.',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
        </svg>
      ),
      suggestions: [
        'Check your internet connection and try again',
        'Wait a few moments and retry the upload',
        'Try refreshing the page if the problem persists'
      ]
    };
  }

  // Duplicate file
  if (errorLower.includes('duplicate') || errorLower.includes('already uploaded')) {
    return {
      title: 'Duplicate File Detected',
      message: 'This file has already been uploaded to the system.',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      ),
      suggestions: [
        'The data from this file is already available for research',
        'Try uploading a different file with new measurements',
        'Check the upload history to verify existing data'
      ]
    };
  }

  // Default generic error
  return {
    title: 'Upload Failed',
    message: error,
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    suggestions: [
      'Please try uploading the file again',
      'Ensure your file is a valid NetCDF format',
      'Contact support if the problem persists'
    ]
  };
};

export const ErrorDisplay = ({ error, type = 'error', onDismiss, className = '' }: ErrorDisplayProps) => {
  if (!error) return null;

  const details = getErrorDetails(error);
  
  const colorClasses = {
    error: 'bg-rose-50 border-rose-200 text-rose-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800'
  };

  const iconColorClasses = {
    error: 'text-rose-500',
    warning: 'text-amber-500', 
    info: 'text-blue-500'
  };

  return (
    <div className={`rounded-2xl border-2 p-6 ${colorClasses[type]} ${className}`}>
      <div className="flex items-start gap-4">
        <div className={`flex-shrink-0 w-10 h-10 rounded-xl bg-white/60 flex items-center justify-center ${iconColorClasses[type]}`}>
          {details.icon}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="font-bold text-lg mb-1">{details.title}</h3>
              <p className="text-sm leading-relaxed mb-4">{details.message}</p>
              
              {details.suggestions && details.suggestions.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-semibold">What you can try:</p>
                  <ul className="text-sm space-y-1 ml-2">
                    {details.suggestions.map((suggestion, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-current opacity-60 mt-1.5 flex-shrink-0">•</span>
                        <span>{suggestion}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="flex-shrink-0 p-1 hover:bg-white/40 rounded-lg transition-colors duration-200"
                aria-label="Dismiss error"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};