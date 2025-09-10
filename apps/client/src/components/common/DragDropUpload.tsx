import { useState, useRef, useCallback } from 'react';

interface DragDropUploadProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  accept?: string;
  maxSize?: number;
  className?: string;
}

export const DragDropUpload = ({ 
  onFileSelect, 
  disabled = false, 
  accept = '.nc,.netcdf',
  maxSize = 50 * 1024 * 1024, // 50MB
  className = ''
}: DragDropUploadProps) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback((file: File): string | null => {
    if (!file.name.match(/\.(nc|netcdf)$/i)) {
      return 'Please select a NetCDF file (.nc or .netcdf)';
    }
    if (file.size > maxSize) {
      return `File size must be less than ${Math.round(maxSize / (1024 * 1024))}MB`;
    }
    return null;
  }, [maxSize]);

  const handleFileSelection = useCallback((file: File) => {
    const error = validateFile(file);
    if (error) {
      alert(error); // TODO: Replace with proper error handling
      return;
    }
    onFileSelect(file);
  }, [onFileSelect, validateFile]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragOver(true);
    }
  }, []);

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    if (disabled) return;
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleFileSelection(file);
    }
  }, [disabled, handleFileSelection]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      handleFileSelection(file);
    }
  };

  const openFileDialog = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div className={`relative ${className}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileInput}
        disabled={disabled}
        className="hidden"
        aria-label="File upload input"
      />
      
      <div
        onDragEnter={handleDragIn}
        onDragLeave={handleDragOut}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={openFileDialog}
        className={`
          relative cursor-pointer border-2 border-dashed rounded-2xl p-8 sm:p-12 
          transition-all duration-300 ease-in-out
          ${disabled 
            ? 'opacity-50 cursor-not-allowed bg-slate-50 border-slate-200' 
            : isDragOver 
              ? 'border-indigo-500 bg-indigo-50 shadow-lg shadow-indigo-100 scale-[1.02]' 
              : 'border-slate-300 bg-white hover:border-indigo-400 hover:bg-indigo-25 hover:shadow-md'
          }
        `}
        role="button"
        tabIndex={0}
        aria-label="Click to upload file or drag and drop"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            openFileDialog();
          }
        }}
      >
        {isDragOver && (
          <div className="absolute inset-0 bg-indigo-500/10 rounded-2xl flex items-center justify-center">
            <div className="bg-indigo-500 text-white px-4 py-2 rounded-xl font-semibold shadow-lg animate-pulse">
              Drop your NetCDF file here!
            </div>
          </div>
        )}
        
        <div className="text-center space-y-4">
          <div className={`mx-auto w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300 ${
            isDragOver 
              ? 'bg-indigo-500 text-white scale-110' 
              : 'bg-indigo-100 text-indigo-600'
          }`}>
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          
          <div className="space-y-2">
            <h3 className={`font-bold text-lg transition-colors duration-300 ${
              isDragOver ? 'text-indigo-700' : 'text-slate-800'
            }`}>
              Upload ARGO NetCDF Files
            </h3>
            <p className="text-slate-600 text-sm leading-relaxed">
              Drag and drop your files here, or <span className="text-indigo-600 font-semibold">click to browse</span>
            </p>
          </div>
          
          <div className="flex flex-wrap justify-center gap-2 text-xs text-slate-500">
            <span className="bg-slate-100 px-3 py-1 rounded-full">NetCDF (.nc)</span>
            <span className="bg-slate-100 px-3 py-1 rounded-full">Max 50MB</span>
            <span className="bg-slate-100 px-3 py-1 rounded-full">ARGO Format</span>
          </div>
          
          <div className="pt-4">
            
          </div>
        </div>
      </div>
    </div>
  );
};