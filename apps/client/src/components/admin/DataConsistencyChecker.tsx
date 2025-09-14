import { useState } from 'react';
import { apiService } from '../../services/api';
import { Button } from '../common/Button';

interface ConsistencyCheck {
  passed: boolean;
  details: string;
}

interface ValidationMetrics {
  sample_size_used: number;
  missing_in_vector_store: number;
  hash_mismatches: number;
  field_validation_issues: number;
  count_difference: number;
  count_difference_percentage: number;
  file_upload_consistency: boolean;
}

interface ConsistencyCheckResult {
  overall_status: string;
  consistency_score: number;
  consistency_issues: string[];
  recommendations: string[];
  detailed_analysis: {
    postgresql: {
      total_measurements: number;
      unique_floats: number;
      uploaded_files: number;
      sample_data_count: number;
      sample_size_used?: number;
    };
    chromadb: {
      total_measurements: number;
      searchable_results: number;
      vector_store_error?: string;
      collection_stats: Record<string, unknown>;
    };
    consistency_checks: {
      [key: string]: ConsistencyCheck;
    };
    validation_metrics?: ValidationMetrics;
  };
  test_timestamp: number;
  enhanced_validation?: boolean;
}

interface DataConsistencyCheckerProps {
  onClose: () => void;
}

export const DataConsistencyChecker = ({ onClose }: DataConsistencyCheckerProps) => {
  const [result, setResult] = useState<ConsistencyCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  const runConsistencyCheck = async () => {
    try {
      setLoading(true);
      setError('');
      setResult(null);

      const response = await apiService.checkDataConsistency();
      setResult(response);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to run consistency check';
      setError(errorMessage);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'excellent': return 'text-emerald-800 bg-emerald-100 border-emerald-200';
      case 'good': return 'text-green-800 bg-green-100 border-green-200';
      case 'acceptable': return 'text-yellow-800 bg-yellow-100 border-yellow-200';
      case 'concerning': return 'text-orange-800 bg-orange-100 border-orange-200';
      case 'critical': return 'text-red-800 bg-red-100 border-red-200';
      default: return 'text-slate-800 bg-slate-100 border-slate-200';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 95) return 'text-emerald-600';
    if (score >= 85) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    if (score >= 50) return 'text-orange-600';
    return 'text-red-600';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Data Consistency Check</h2>
            <p className="text-sm text-slate-600 mt-1">
              Verify synchronization between PostgreSQL and ChromaDB
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
        <div className="flex-1 overflow-y-auto p-6">
          {!result && !loading && (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-slate-800 mb-2">Ready to Check Data Consistency</h3>
              <p className="text-slate-600 mb-6 max-w-md mx-auto">
                This will analyze data synchronization between your PostgreSQL database and ChromaDB vector store
                to ensure AI responses are accurate and complete.
              </p>
              <Button onClick={runConsistencyCheck} disabled={loading}>
                Run Consistency Check
              </Button>
            </div>
          )}

          {loading && (
            <div className="text-center py-12">
              <div className="animate-spin w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4"></div>
              <h3 className="font-semibold text-slate-800 mb-2">Analyzing Data Consistency</h3>
              <p className="text-slate-600">This may take a moment while we compare databases...</p>
            </div>
          )}

          {error && (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-slate-800 mb-2">Consistency Check Failed</h3>
              <p className="text-slate-600 mb-4">{error}</p>
              <Button onClick={runConsistencyCheck} variant="secondary">
                Try Again
              </Button>
            </div>
          )}

          {result && (
            <div className="space-y-6">
              {/* Overall Status */}
              <div className={`rounded-2xl border p-6 ${getStatusColor(result.overall_status)}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-lg capitalize">{result.overall_status} Consistency</h3>
                    <p className="text-sm opacity-90">
                      Data synchronization status between PostgreSQL and ChromaDB
                    </p>
                  </div>
                  <div className="text-right">
                    <div className={`text-3xl font-bold ${getScoreColor(result.consistency_score)}`}>
                      {result.consistency_score}/100
                    </div>
                    <div className="text-sm opacity-75">Consistency Score</div>
                  </div>
                </div>
              </div>

              {/* Database Stats Comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* PostgreSQL Stats */}
                <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-indigo-500 rounded-lg flex items-center justify-center">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                      </svg>
                    </div>
                    <div>
                      <h4 className="font-semibold text-indigo-800">PostgreSQL Database</h4>
                      <p className="text-sm text-indigo-600">Primary data storage</p>
                    </div>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-indigo-700">Total measurements:</span>
                      <span className="font-semibold text-indigo-800">
                        {result.detailed_analysis.postgresql.total_measurements.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-indigo-700">Unique floats:</span>
                      <span className="font-semibold text-indigo-800">
                        {result.detailed_analysis.postgresql.unique_floats}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-indigo-700">Uploaded files:</span>
                      <span className="font-semibold text-indigo-800">
                        {result.detailed_analysis.postgresql.uploaded_files}
                      </span>
                    </div>
                  </div>
                </div>

                {/* ChromaDB Stats */}
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-emerald-500 rounded-lg flex items-center justify-center">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </div>
                    <div>
                      <h4 className="font-semibold text-emerald-800">ChromaDB Vector Store</h4>
                      <p className="text-sm text-emerald-600">AI search index</p>
                    </div>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-emerald-700">Vector measurements:</span>
                      <span className="font-semibold text-emerald-800">
                        {result.detailed_analysis.chromadb.total_measurements.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-emerald-700">Searchable results:</span>
                      <span className="font-semibold text-emerald-800">
                        {result.detailed_analysis.chromadb.searchable_results}
                      </span>
                    </div>
                    {result.detailed_analysis.chromadb.vector_store_error && (
                      <div className="text-red-600 text-xs">
                        Error: {result.detailed_analysis.chromadb.vector_store_error}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Consistency Issues */}
              {result.consistency_issues.length > 0 && (
                <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
                  <h4 className="font-semibold text-orange-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Consistency Issues Found
                  </h4>
                  <ul className="space-y-2">
                    {result.consistency_issues.map((issue, index) => (
                      <li key={index} className="text-sm text-orange-700 flex items-start gap-2">
                        <span className="w-2 h-2 bg-orange-400 rounded-full flex-shrink-0 mt-1.5"></span>
                        {issue}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommendations */}
              {result.recommendations.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <h4 className="font-semibold text-blue-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Recommendations
                  </h4>
                  <ul className="space-y-2">
                    {result.recommendations.map((recommendation, index) => (
                      <li key={index} className="text-sm text-blue-700 flex items-start gap-2">
                        <span className="w-2 h-2 bg-blue-400 rounded-full flex-shrink-0 mt-1.5"></span>
                        {recommendation}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Detailed Analysis */}
              <details className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                <summary className="font-semibold text-slate-800 cursor-pointer">
                  View Detailed Analysis
                </summary>
                <div className="mt-4 space-y-4 text-sm">
                  <div>
                    <h5 className="font-semibold text-slate-700 mb-2">Enhanced Consistency Checks</h5>
                    <div className="space-y-2">
                      {Object.entries(result.detailed_analysis.consistency_checks).map(([checkName, check]) => (
                        <div key={checkName} className="flex items-center justify-between p-2 rounded border">
                          <span className="capitalize">{checkName.replace(/_/g, ' ')}</span>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              check.passed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {check.passed ? 'PASSED' : 'FAILED'}
                            </span>
                            <span className="text-xs text-slate-600">{check.details}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {result.detailed_analysis.validation_metrics && (
                    <div>
                      <h5 className="font-semibold text-slate-700 mb-2">Validation Metrics</h5>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="flex justify-between">
                          <span>Sample size used:</span>
                          <span className="font-medium">{result.detailed_analysis.validation_metrics.sample_size_used}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Count difference:</span>
                          <span className="font-medium">{result.detailed_analysis.validation_metrics.count_difference}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Percentage difference:</span>
                          <span className="font-medium">{result.detailed_analysis.validation_metrics.count_difference_percentage}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Missing in vector store:</span>
                          <span className="font-medium">{result.detailed_analysis.validation_metrics.missing_in_vector_store}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Hash mismatches:</span>
                          <span className="font-medium">{result.detailed_analysis.validation_metrics.hash_mismatches}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Field validation issues:</span>
                          <span className="font-medium">{result.detailed_analysis.validation_metrics.field_validation_issues}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>File upload consistency:</span>
                          <span className={`font-medium ${result.detailed_analysis.validation_metrics.file_upload_consistency ? 'text-green-600' : 'text-red-600'}`}>
                            {result.detailed_analysis.validation_metrics.file_upload_consistency ? 'Good' : 'Issues'}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {result.enhanced_validation && (
                    <div className="text-xs text-emerald-600 font-medium">
                      ✓ Enhanced validation with improved edge case handling
                    </div>
                  )}
                  
                  <div className="text-xs text-slate-500">
                    Test completed at: {new Date(result.test_timestamp * 1000).toLocaleString()}
                  </div>
                </div>
              </details>

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <Button onClick={runConsistencyCheck} variant="secondary" className="flex-1">
                  Run Check Again
                </Button>
                <Button onClick={onClose} className="flex-1">
                  Close Report
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};