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
      
      setIsUploading(false);
    } catch (error) {
      console.error('Upload error:', error);
      setStatus('Upload failed. Please try again.');
      setUploadDetails(null);
      setIsUploading(false); // Immediately stop on error
    }
  };

  const uploadMultipleFiles = async (files: File[]): Promise<void> => {
    setIsUploading(true);
    setStatus(`Uploading ${files.length} files...`);
    setUploadDetails(null);

    let totalAdded = 0;
    let totalDuplicates = 0;
    let totalFailed = 0;
    const fileResults: string[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setStatus(`Processing file ${i + 1} of ${files.length}: ${file.name}...`);
      try {
        const response = await apiService.uploadFile(file);
        const added = response.measurements_count ?? 0;
        const dupes = response.duplicate_measurements ?? 0;
        totalAdded += added;
        totalDuplicates += dupes;
        if (response.status === 'duplicate_file') {
          fileResults.push(`${file.name}: duplicate file skipped`);
        } else {
          fileResults.push(`${file.name}: +${added} new, ${dupes} duplicates skipped`);
        }
      } catch (err) {
        totalFailed++;
        fileResults.push(`${file.name}: FAILED`);
        console.error(`Failed to upload ${file.name}:`, err);
      }
    }

    const successCount = files.length - totalFailed;
    setStatus(
      `Batch upload complete! ${successCount}/${files.length} files processed. ` +
      `${totalAdded} new measurements added, ${totalDuplicates} duplicates skipped.` +
      (totalFailed > 0 ? ` ${totalFailed} file(s) failed.` : '')
    );
    setUploadDetails({
      measurements_count: totalAdded,
      duplicate_measurements: totalDuplicates,
      total_in_file: totalAdded + totalDuplicates,
      status: totalFailed === 0 ? 'success' : 'partial_success',
      message: fileResults.join('\n'),
    } as UploadResponse);
    setIsUploading(false);
  };

  return {
    status,
    isUploading,
    uploadFile,
    uploadMultipleFiles,
    uploadDetails,
  };
};