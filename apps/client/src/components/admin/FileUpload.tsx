import React from 'react';
import type { UploadResponse } from '../../types';
import { DragDropUpload } from '../common/DragDropUpload';
import { ErrorDisplay } from '../common/ErrorDisplay';

interface FileUploadProps {
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  status: string;
  uploadDetails?: UploadResponse | null;
  isUploading?: boolean;
}

export const FileUpload = ({ onFileChange, status, uploadDetails, isUploading }: FileUploadProps) => {
  const handleFileSelect = (file: File) => {
    const event = {
      target: { files: [file] }
    } as unknown as React.ChangeEvent<HTMLInputElement>;
    onFileChange(event);
  };

  const isError = status && (
    status.toLowerCase().includes('error') || 
    status.toLowerCase().includes('failed') || 
    status.toLowerCase().includes('invalid')
  ) && !isUploading;

  const isSuccess = status && (
    status.toLowerCase().includes('success') || 
    status.toLowerCase().includes('uploaded') || 
    status.toLowerCase().includes('added') ||
    status.toLowerCase().includes('completed')
  ) && !isUploading;

  const isDuplicate = status && (
    status.toLowerCase().includes('duplicate') || 
    status.toLowerCase().includes('already')
  ) && !isUploading;

  return (
    <div className="space-y-6">
      <div className="text-center">
        <p className="text-slate-600 text-lg leading-relaxed max-w-2xl mx-auto">
          Upload ARGO NetCDF files for processing and analysis. Our system automatically validates data, 
          detects duplicates, and makes your ocean measurements searchable.
        </p>
      </div>
      
      {!isUploading && !isSuccess && !isDuplicate && !isError && (
        <DragDropUpload
          onFileSelect={handleFileSelect}
          disabled={isUploading}
          className="max-w-2xl mx-auto"
        />
      )}

      {isUploading && (
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-2xl border border-indigo-100 shadow-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-indigo-500 rounded-xl flex items-center justify-center">
                <svg className="w-4 h-4 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <h3 className="font-bold text-lg text-slate-800">Processing Upload</h3>
            </div>
            <p className="text-slate-600">{status}</p>
          </div>
        </div>
      )}
      
      {isError && (
        <div className="max-w-2xl mx-auto">
          <ErrorDisplay error={status} />
        </div>
      )}
      
      {(isSuccess || isDuplicate) && (
        <div className="max-w-2xl mx-auto">
          <div className={`rounded-2xl border-2 p-6 ${
            isSuccess 
              ? 'bg-emerald-50 border-emerald-200' 
              : 'bg-amber-50 border-amber-200'
          }`}>
            <div className="flex items-start gap-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                isSuccess 
                  ? 'bg-emerald-500 text-white' 
                  : 'bg-amber-500 text-white'
              }`}>
                {isSuccess ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
              </div>
              
              <div className="flex-1">
                <h3 className={`font-bold text-lg mb-2 ${
                  isSuccess ? 'text-emerald-800' : 'text-amber-800'
                }`}>
                  {isSuccess ? 'Upload Successful!' : 'Duplicate Detected'}
                </h3>
                <p className={`text-sm mb-4 ${
                  isSuccess ? 'text-emerald-700' : 'text-amber-700'
                }`}>
                  {status}
                </p>
                
                {uploadDetails && (
                  <div className="bg-white/60 rounded-xl p-4 space-y-2">
                    <h4 className={`font-semibold ${
                      isSuccess ? 'text-emerald-800' : 'text-amber-800'
                    }`}>
                      Processing Summary
                    </h4>
                    <div className={`grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm ${
                      isSuccess ? 'text-emerald-700' : 'text-amber-700'
                    }`}>
                      {uploadDetails.measurements_count !== undefined && (
                        <div className="flex justify-between">
                          <span>New measurements:</span>
                          <span className="font-semibold">{uploadDetails.measurements_count}</span>
                        </div>
                      )}
                      {uploadDetails.duplicate_measurements !== undefined && uploadDetails.duplicate_measurements > 0 && (
                        <div className="flex justify-between">
                          <span>Duplicates skipped:</span>
                          <span className="font-semibold">{uploadDetails.duplicate_measurements}</span>
                        </div>
                      )}
                      {uploadDetails.total_in_file !== undefined && (
                        <div className="flex justify-between">
                          <span>Total in file:</span>
                          <span className="font-semibold">{uploadDetails.total_in_file}</span>
                        </div>
                      )}
                      {uploadDetails.vector_stats && (
                        <div className="flex justify-between">
                          <span>Vector duplicates:</span>
                          <span className="font-semibold">{uploadDetails.vector_stats.duplicates_skipped}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};