import type { UploadResponse } from '../../types';

interface FileUploadProps {
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  status: string;
  uploadDetails?: UploadResponse | null;
  isUploading?: boolean;
}

export const FileUpload = ({ onFileChange, status, uploadDetails, isUploading }: FileUploadProps) => {
  return (
    <div className="space-y-4">
      <div className="text-center sm:text-left">
        <h2 className="text-xl sm:text-2xl font-semibold text-gray-900 mb-2">
          Upload ARGO NetCDF Files
        </h2>
        <p className="text-sm text-gray-600 mb-4">
          Select NetCDF files containing ARGO ocean data for processing. Duplicate files and measurements will be automatically detected and skipped.
        </p>
      </div>
      
      <div className="relative">
        <input
          type="file"
          accept=".nc,.netcdf"
          onChange={onFileChange}
          disabled={isUploading}
          className={`block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 ${
            isUploading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          aria-describedby="file-upload-help"
        />
        <p className="mt-2 text-xs text-gray-500" id="file-upload-help">
          Supported formats: .nc, .netcdf (Max file size: 50MB)
        </p>
      </div>
      
      {status && (
        <div className={`p-3 rounded-lg text-sm font-medium ${
          status.toLowerCase().includes('error') || status.toLowerCase().includes('failed')
            ? 'bg-red-50 text-red-800 border border-red-200'
            : status.toLowerCase().includes('success') || status.toLowerCase().includes('uploaded') || status.toLowerCase().includes('added')
            ? 'bg-green-50 text-green-800 border border-green-200'
            : status.toLowerCase().includes('duplicate') || status.toLowerCase().includes('already')
            ? 'bg-yellow-50 text-yellow-800 border border-yellow-200'
            : 'bg-blue-50 text-blue-800 border border-blue-200'
        }`}>
          {status}
        </div>
      )}
      
      {uploadDetails && (
        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
          <h3 className="text-sm font-medium text-gray-900 mb-2">Upload Details</h3>
          <div className="space-y-1 text-xs text-gray-600">
            {uploadDetails.measurements_count !== undefined && (
              <div>New measurements added: <span className="font-medium text-green-600">{uploadDetails.measurements_count}</span></div>
            )}
            {uploadDetails.duplicate_measurements !== undefined && uploadDetails.duplicate_measurements > 0 && (
              <div>Duplicate measurements skipped: <span className="font-medium text-yellow-600">{uploadDetails.duplicate_measurements}</span></div>
            )}
            {uploadDetails.total_in_file !== undefined && (
              <div>Total measurements in file: <span className="font-medium">{uploadDetails.total_in_file}</span></div>
            )}
            {uploadDetails.vector_stats && (
              <div>Vector store duplicates skipped: <span className="font-medium text-yellow-600">{uploadDetails.vector_stats.duplicates_skipped}</span></div>
            )}
            {uploadDetails.status && (
              <div>Status: <span className={`font-medium ${
                uploadDetails.status === 'completed' ? 'text-green-600' :
                uploadDetails.status === 'duplicate_file' ? 'text-yellow-600' :
                uploadDetails.status === 'all_duplicates' ? 'text-yellow-600' : 'text-blue-600'
              }`}>{uploadDetails.status.replace('_', ' ')}</span></div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};