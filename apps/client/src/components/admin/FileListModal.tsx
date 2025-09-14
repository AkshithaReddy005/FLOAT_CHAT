import { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import { Button } from '../common/Button';

interface UploadedFile {
  id: number;
  filename: string;
  file_hash: string;
  file_size: number;
  upload_date: string;
  measurements_count: number;
}

interface FileListResponse {
  files: UploadedFile[];
  total_files: number;
}

interface FileListModalProps {
  onClose: () => void;
}

export const FileListModal = ({ onClose }: FileListModalProps) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalFiles, setTotalFiles] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const filesPerPage = 20;

  const loadFiles = async (skip: number = 0) => {
    try {
      setLoading(true);
      const response: FileListResponse = await apiService.getUploadedFiles(skip, filesPerPage);
      setFiles(response.files);
      setTotalFiles(response.total_files);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Failed to load files');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles((currentPage - 1) * filesPerPage);
  }, [currentPage]);

  const formatFileSize = (bytes: number): string => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const totalPages = Math.ceil(totalFiles / filesPerPage);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Uploaded Files</h2>
            <p className="text-sm text-slate-600 mt-1">
              {totalFiles > 0 ? `${totalFiles} files total` : 'No files uploaded yet'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 rounded-xl bg-slate-100 hover:bg-slate-200 flex items-center justify-center transition-colors"
          >
            <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="flex items-center gap-3">
                <div className="animate-spin w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full"></div>
                <span className="text-slate-600">Loading files...</span>
              </div>
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-slate-800 mb-2">Failed to Load Files</h3>
                <p className="text-slate-600 mb-4">{error}</p>
                <Button onClick={() => loadFiles((currentPage - 1) * filesPerPage)} variant="secondary">
                  Try Again
                </Button>
              </div>
            </div>
          ) : files.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-slate-800 mb-2">No Files Uploaded</h3>
                <p className="text-slate-600">Upload some NetCDF files to see them here.</p>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              <div className="p-6">
                {/* Files Table Header */}
                <div className="grid grid-cols-12 gap-4 text-xs font-semibold text-slate-600 uppercase tracking-wider mb-4 px-4">
                  <div className="col-span-4">Filename</div>
                  <div className="col-span-2">Size</div>
                  <div className="col-span-2">Measurements</div>
                  <div className="col-span-3">Upload Date</div>
                  <div className="col-span-1">Hash ID</div>
                </div>

                {/* Files List */}
                <div className="space-y-2">
                  {files.map((file) => (
                    <div
                      key={file.id}
                      className="grid grid-cols-12 gap-4 items-center bg-slate-50 hover:bg-slate-100 rounded-xl p-4 transition-colors"
                    >
                      <div className="col-span-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center flex-shrink-0">
                            <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                            </svg>
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-slate-800 text-sm truncate" title={file.filename}>
                              {file.filename}
                            </p>
                            <p className="text-xs text-slate-600">File ID: {file.id}</p>
                          </div>
                        </div>
                      </div>
                      <div className="col-span-2">
                        <span className="text-sm font-medium text-slate-700">
                          {formatFileSize(file.file_size)}
                        </span>
                      </div>
                      <div className="col-span-2">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                          {file.measurements_count.toLocaleString()} measurements
                        </span>
                      </div>
                      <div className="col-span-3">
                        <span className="text-sm text-slate-600">
                          {formatDate(file.upload_date)}
                        </span>
                      </div>
                      <div className="col-span-1">
                        <span className="text-xs font-mono text-slate-500 bg-slate-100 px-2 py-1 rounded">
                          {file.file_hash}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer with Pagination */}
        {!loading && !error && totalPages > 1 && (
          <div className="border-t border-slate-200 p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-600">
                Showing {((currentPage - 1) * filesPerPage) + 1} to {Math.min(currentPage * filesPerPage, totalFiles)} of {totalFiles} files
              </p>
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  variant="secondary"
                  className="text-sm px-3 py-2"
                >
                  Previous
                </Button>
                <span className="text-sm text-slate-600">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  variant="secondary"
                  className="text-sm px-3 py-2"
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};