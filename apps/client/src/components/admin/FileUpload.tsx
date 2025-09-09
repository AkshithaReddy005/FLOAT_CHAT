interface FileUploadProps {
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  status: string;
}

export const FileUpload = ({ onFileChange, status }: FileUploadProps) => {
  return (
    <div className="space-y-4">
      <div className="text-center sm:text-left">
        <h2 className="text-xl sm:text-2xl font-semibold text-gray-900 mb-2">
          Upload ARGO NetCDF Files
        </h2>
        <p className="text-sm text-gray-600 mb-4">
          Select NetCDF files containing ARGO ocean data for processing
        </p>
      </div>
      
      <div className="relative">
        <input
          type="file"
          accept=".nc,.netcdf"
          onChange={onFileChange}
          className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
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
            : status.toLowerCase().includes('success') || status.toLowerCase().includes('uploaded')
            ? 'bg-green-50 text-green-800 border border-green-200'
            : 'bg-blue-50 text-blue-800 border border-blue-200'
        }`}>
          {status}
        </div>
      )}
    </div>
  );
};