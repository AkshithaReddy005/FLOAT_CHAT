import { useState } from 'react';
import { apiService } from '../services/api';

export const useUpload = () => {
  const [status, setStatus] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);

  const uploadFile = async (file: File): Promise<void> => {
    setIsUploading(true);
    setStatus('Uploading...');
    
    try {
      await apiService.uploadFile(file);
      setStatus('Upload successful! Data processed and available to researchers.');
    } catch (error) {
      console.error('Upload error:', error);
      setStatus('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return {
    status,
    isUploading,
    uploadFile,
  };
};