import { useState } from 'react';
import { apiService } from '../services/api';
import type { UploadResponse } from '../types';

export const useUpload = () => {
  const [status, setStatus] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadDetails, setUploadDetails] = useState<UploadResponse | null>(null);

  const uploadFile = async (file: File): Promise<void> => {
    setIsUploading(true);
    setStatus('Uploading and processing file...');
    setUploadDetails(null);
    
    try {
      const response = await apiService.uploadFile(file);
      setUploadDetails(response);
      
      // Create detailed status message based on response
      if (response.status === 'duplicate_file') {
        setStatus(`File already uploaded previously on ${new Date(response.original_upload_date!).toLocaleDateString()}. No new data added.`);
      } else if (response.status === 'all_duplicates') {
        setStatus(`All ${response.total_in_file} measurements in this file already exist in the system. No new data added.`);
      } else if (response.duplicate_measurements && response.duplicate_measurements > 0) {
        setStatus(`Upload successful! Added ${response.measurements_count} new measurements. Skipped ${response.duplicate_measurements} duplicates. Data is available to researchers.`);
      } else {
        setStatus(`Upload successful! Added ${response.measurements_count} new measurements. Data is available to researchers.`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      setStatus('Upload failed. Please try again.');
      setUploadDetails(null);
    } finally {
      setIsUploading(false);
    }
  };

  return {
    status,
    isUploading,
    uploadFile,
    uploadDetails,
  };
};