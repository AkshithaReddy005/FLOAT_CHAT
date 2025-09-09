import { useState, useEffect } from 'react';
import { Layout } from '../common/Layout';
import { FileUpload } from './FileUpload';
import { useUpload } from '../../hooks/useUpload';
import { apiService } from '../../services/api';
import { Button } from '../common/Button';

interface DatabaseStats {
  total_measurements: number;
  unique_floats: number;
  total_files_uploaded: number;
  vector_store: {
    total_measurements: number;
    collection_name: string;
  };
  latest_upload?: {
    filename: string;
    upload_date: string;
    measurements_count: number;
  } | null;
}

export const AdminDashboard = () => {
  const { status, uploadFile, uploadDetails, isUploading } = useUpload();
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [isClearingDatabases, setIsClearingDatabases] = useState(false);
  const [clearStatus, setClearStatus] = useState<string>('');
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      uploadFile(file);
    }
  };

  const loadStats = async () => {
    setStatsLoading(true);
    try {
      const response = await apiService.getStats();
      setStats(response);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setStatsLoading(false);
    }
  };

  const handleClearAllDatabases = async () => {
    setIsClearingDatabases(true);
    setClearStatus('Clearing all databases...');
    
    try {
      const response = await apiService.clearAllDatabases();
      setClearStatus(response.message);
      
      // Reload stats after clearing
      setTimeout(loadStats, 1000);
      
      // Clear the status after 5 seconds
      setTimeout(() => {
        setClearStatus('');
      }, 5000);
      
    } catch (error: any) {
      setClearStatus(`Failed to clear databases: ${error.message}`);
      setTimeout(() => {
        setClearStatus('');
      }, 10000);
    } finally {
      setIsClearingDatabases(false);
      setShowClearConfirm(false);
    }
  };

  // Load stats on component mount and after successful uploads
  useEffect(() => {
    loadStats();
  }, []);

  // Reload stats after successful upload
  useEffect(() => {
    if (status.includes('successful') || status.includes('duplicate')) {
      setTimeout(loadStats, 2000); // Give server time to process
    }
  }, [status]);

  return (
    <Layout title="Admin Dashboard">
      <div className="space-y-8">
        {/* Database Stats Section */}
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-slate-800">Database Statistics</h2>
            <div className="flex gap-2">
              <Button
                onClick={loadStats}
                disabled={statsLoading}
                variant="secondary"
                className="text-sm"
              >
                {statsLoading ? 'Refreshing...' : 'Refresh Stats'}
              </Button>
              
              <Button
                onClick={() => setShowClearConfirm(true)}
                disabled={isClearingDatabases}
                variant="danger"
                className="text-sm"
              >
                Clear All Data
              </Button>
            </div>
          </div>

          {stats ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-indigo-500 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-indigo-800">PostgreSQL</p>
                    <p className="text-2xl font-bold text-indigo-900">{stats.total_measurements.toLocaleString()}</p>
                    <p className="text-xs text-indigo-600">measurements</p>
                  </div>
                </div>
              </div>

              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-emerald-500 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-emerald-800">ChromaDB</p>
                    <p className="text-2xl font-bold text-emerald-900">{stats.vector_store.total_measurements.toLocaleString()}</p>
                    <p className="text-xs text-emerald-600">vectors</p>
                  </div>
                </div>
              </div>

              <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-purple-800">Files</p>
                    <p className="text-2xl font-bold text-purple-900">{stats.total_files_uploaded}</p>
                    <p className="text-xs text-purple-600">uploaded</p>
                  </div>
                </div>
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-amber-500 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-amber-800">Unique Floats</p>
                    <p className="text-2xl font-bold text-amber-900">{stats.unique_floats}</p>
                    <p className="text-xs text-amber-600">instruments</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-8">
              <div className="animate-pulse text-slate-500">Loading statistics...</div>
            </div>
          )}

          {stats?.latest_upload && (
            <div className="mt-6 pt-6 border-t border-slate-200">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Latest Upload</h3>
              <div className="bg-slate-50 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-slate-800">{stats.latest_upload.filename}</p>
                    <p className="text-sm text-slate-600">
                      {new Date(stats.latest_upload.upload_date).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-slate-800">{stats.latest_upload.measurements_count} measurements</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {clearStatus && (
            <div className="mt-6 pt-6 border-t border-slate-200">
              <div className={`rounded-xl p-4 ${
                clearStatus.includes('successfully') 
                  ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
                  : clearStatus.includes('Failed') 
                    ? 'bg-red-50 border border-red-200 text-red-800'
                    : 'bg-blue-50 border border-blue-200 text-blue-800'
              }`}>
                <p className="font-medium">{clearStatus}</p>
              </div>
            </div>
          )}
        </div>

        {/* File Upload Section */}
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <h2 className="text-xl font-bold text-slate-800 mb-6">Upload NetCDF Files</h2>
          <FileUpload 
            onFileChange={handleFileChange} 
            status={status} 
            uploadDetails={uploadDetails}
            isUploading={isUploading}
          />
        </div>

        {/* Clear Confirmation Modal */}
        {showClearConfirm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl max-w-md w-full mx-4 p-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-lg text-slate-800 mb-2">Clear All Databases</h3>
                  <p className="text-slate-600 mb-6">
                    This will permanently delete all data from both PostgreSQL and ChromaDB. 
                    This action cannot be undone.
                  </p>
                  <div className="bg-slate-50 rounded-lg p-3 mb-6">
                    <p className="text-sm text-slate-700">
                      <strong>What will be deleted:</strong>
                    </p>
                    <ul className="text-sm text-slate-600 mt-1 space-y-1">
                      <li>• All ARGO measurements from PostgreSQL</li>
                      <li>• All uploaded file records</li>
                      <li>• All search vectors from ChromaDB</li>
                      <li>• All duplicate detection cache</li>
                    </ul>
                  </div>
                  <div className="flex gap-3">
                    <Button
                      onClick={handleClearAllDatabases}
                      variant="danger"
                      disabled={isClearingDatabases}
                      className="flex-1"
                    >
                      {isClearingDatabases ? 'Clearing...' : 'Yes, Clear All Data'}
                    </Button>
                    <Button
                      onClick={() => setShowClearConfirm(false)}
                      variant="secondary"
                      disabled={isClearingDatabases}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};