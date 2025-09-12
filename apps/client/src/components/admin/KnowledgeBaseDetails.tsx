import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import { Button } from '../common/Button';

interface KnowledgeBaseData {
  knowledge_base_overview: {
    vector_store: {
      total_measurements: number;
      collection_name: string;
    };
    database_measurements: number;
    unique_instruments: number;
    data_coverage_percentage: number;
  };
  depth_distribution: Array<{
    category: string;
    count: number;
    min_depth: number | null;
    max_depth: number | null;
    avg_depth: number | null;
  }>;
  geographic_distribution: Array<{
    region: string;
    measurement_count: number;
    float_count: number;
    lat_range: [number, number] | null;
    lon_range: [number, number] | null;
  }>;
  parameter_coverage: {
    total_measurements: number;
    temperature_coverage: number;
    salinity_coverage: number;
    pressure_coverage: number;
    ranges: {
      temperature: {
        avg: number | null;
        min: number | null;
        max: number | null;
      };
      salinity: {
        avg: number | null;
        min: number | null;
        max: number | null;
      };
    };
  };
  temporal_distribution: Array<{
    month: string | null;
    measurement_count: number;
    active_floats: number;
  }>;
  rag_insights: {
    vector_embeddings_quality: string;
    search_capabilities: string[];
    sample_vector_content: string[];
  };
  data_quality_indicators: {
    completeness_score: number;
    geographic_coverage: number;
    depth_coverage: number;
    vector_db_sync: number;
  };
}

interface KnowledgeBaseDetailsProps {
  onClose: () => void;
}

export const KnowledgeBaseDetails: React.FC<KnowledgeBaseDetailsProps> = ({ onClose }) => {
  const [data, setData] = useState<KnowledgeBaseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'distribution' | 'rag' | 'quality'>('overview');
  const [balanceTestResult, setBalanceTestResult] = useState<any>(null);
  const [testingBalance, setTestingBalance] = useState(false);

  const loadKnowledgeBaseData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getKnowledgeBaseDetails();
      setData(response);
    } catch (err: any) {
      setError(err.message || 'Failed to load knowledge base details');
    } finally {
      setLoading(false);
    }
  };

  const testRAGBalance = async () => {
    setTestingBalance(true);
    try {
      const result = await apiService.testRAGBalance();
      setBalanceTestResult(result);
    } catch (err: any) {
      setError(err.message || 'Failed to test RAG balance');
    } finally {
      setTestingBalance(false);
    }
  };

  useEffect(() => {
    loadKnowledgeBaseData();
  }, []);

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  const getQualityColor = (score: number) => {
    if (score >= 90) return 'text-emerald-600 bg-emerald-50 border-emerald-200';
    if (score >= 70) return 'text-amber-600 bg-amber-50 border-amber-200';
    return 'text-red-600 bg-red-50 border-red-200';
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl max-w-6xl w-full mx-4 p-8">
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            <span className="ml-4 text-lg text-slate-600">Loading knowledge base details...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl max-w-2xl w-full mx-4 p-8">
          <div className="text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-slate-800 mb-2">Error Loading Data</h3>
            <p className="text-slate-600 mb-6">{error}</p>
            <div className="flex gap-3 justify-center">
              <Button onClick={loadKnowledgeBaseData} variant="primary">Try Again</Button>
              <Button onClick={onClose} variant="secondary">Close</Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-7xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div>
            <h2 className="text-2xl font-bold text-slate-800">RAG Knowledge Base Details</h2>
            <p className="text-slate-600">Comprehensive analysis of your ARGO data knowledge base</p>
          </div>
          <div className="flex gap-3">
            <Button onClick={loadKnowledgeBaseData} variant="secondary" className="text-sm">
              Refresh
            </Button>
            <Button onClick={onClose} variant="secondary" className="text-sm">
              Close
            </Button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-slate-200">
          <nav className="flex px-6">
            {[
              { key: 'overview', label: 'Overview' },
              { key: 'distribution', label: 'Data Distribution' },
              { key: 'rag', label: 'RAG Insights' },
              { key: 'quality', label: 'Quality Metrics' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Knowledge Base Overview */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-6">
                  <div className="text-center">
                    <div className="w-12 h-12 bg-indigo-500 rounded-lg flex items-center justify-center mx-auto mb-3">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-indigo-800">Vector Store</p>
                    <p className="text-2xl font-bold text-indigo-900">{formatNumber(data.knowledge_base_overview.vector_store.total_measurements)}</p>
                    <p className="text-xs text-indigo-600">embedded vectors</p>
                  </div>
                </div>

                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6">
                  <div className="text-center">
                    <div className="w-12 h-12 bg-emerald-500 rounded-lg flex items-center justify-center mx-auto mb-3">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-emerald-800">Total Measurements</p>
                    <p className="text-2xl font-bold text-emerald-900">{formatNumber(data.knowledge_base_overview.database_measurements)}</p>
                    <p className="text-xs text-emerald-600">in database</p>
                  </div>
                </div>

                <div className="bg-purple-50 border border-purple-200 rounded-xl p-6">
                  <div className="text-center">
                    <div className="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center mx-auto mb-3">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-purple-800">ARGO Floats</p>
                    <p className="text-2xl font-bold text-purple-900">{data.knowledge_base_overview.unique_instruments}</p>
                    <p className="text-xs text-purple-600">unique instruments</p>
                  </div>
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
                  <div className="text-center">
                    <div className="w-12 h-12 bg-amber-500 rounded-lg flex items-center justify-center mx-auto mb-3">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-amber-800">Vector Coverage</p>
                    <p className="text-2xl font-bold text-amber-900">{data.knowledge_base_overview.data_coverage_percentage}%</p>
                    <p className="text-xs text-amber-600">data vectorized</p>
                  </div>
                </div>
              </div>

              {/* Parameter Coverage */}
              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Parameter Coverage</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-slate-700">Temperature</span>
                      <span className="text-sm font-bold text-slate-800">{data.parameter_coverage.temperature_coverage}%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2">
                      <div 
                        className="bg-red-400 h-2 rounded-full" 
                        style={{ width: `${data.parameter_coverage.temperature_coverage}%` }}
                      ></div>
                    </div>
                    {data.parameter_coverage.ranges.temperature.avg && (
                      <p className="text-xs text-slate-600 mt-1">
                        Range: {data.parameter_coverage.ranges.temperature.min?.toFixed(1)}°C to {data.parameter_coverage.ranges.temperature.max?.toFixed(1)}°C
                      </p>
                    )}
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-slate-700">Salinity</span>
                      <span className="text-sm font-bold text-slate-800">{data.parameter_coverage.salinity_coverage}%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2">
                      <div 
                        className="bg-blue-400 h-2 rounded-full" 
                        style={{ width: `${data.parameter_coverage.salinity_coverage}%` }}
                      ></div>
                    </div>
                    {data.parameter_coverage.ranges.salinity.avg && (
                      <p className="text-xs text-slate-600 mt-1">
                        Range: {data.parameter_coverage.ranges.salinity.min?.toFixed(2)} to {data.parameter_coverage.ranges.salinity.max?.toFixed(2)}
                      </p>
                    )}
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-slate-700">Pressure</span>
                      <span className="text-sm font-bold text-slate-800">{data.parameter_coverage.pressure_coverage}%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2">
                      <div 
                        className="bg-green-400 h-2 rounded-full" 
                        style={{ width: `${data.parameter_coverage.pressure_coverage}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'distribution' && (
            <div className="space-y-6">
              {/* Depth Distribution */}
              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Depth Distribution</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                  {data.depth_distribution.map((depth, idx) => (
                    <div key={idx} className="bg-slate-50 rounded-lg p-4">
                      <h4 className="font-semibold text-slate-800 capitalize mb-2">{depth.category}</h4>
                      <p className="text-2xl font-bold text-indigo-600 mb-1">{formatNumber(depth.count)}</p>
                      <p className="text-xs text-slate-600">
                        {depth.min_depth !== null && depth.max_depth !== null 
                          ? `${depth.min_depth.toFixed(0)}m - ${depth.max_depth.toFixed(0)}m`
                          : 'No depth data'
                        }
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Geographic Distribution */}
              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Geographic Distribution</h3>
                <div className="space-y-3">
                  {data.geographic_distribution.map((region, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div>
                        <h4 className="font-semibold text-slate-800">{region.region}</h4>
                        <p className="text-sm text-slate-600">
                          {region.measurement_count.toLocaleString()} measurements from {region.float_count} floats
                        </p>
                      </div>
                      <div className="text-right">
                        {region.lat_range && region.lon_range && (
                          <p className="text-xs text-slate-500">
                            {region.lat_range[0].toFixed(1)}°N to {region.lat_range[1].toFixed(1)}°N<br/>
                            {region.lon_range[0].toFixed(1)}°E to {region.lon_range[1].toFixed(1)}°E
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Temporal Distribution */}
              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Recent Temporal Distribution</h3>
                <div className="space-y-2">
                  {data.temporal_distribution.slice(0, 6).map((temporal, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 border-b border-slate-100 last:border-b-0">
                      <span className="text-sm font-medium text-slate-700">
                        {temporal.month ? new Date(temporal.month).toLocaleDateString('en-US', { year: 'numeric', month: 'long' }) : 'Unknown'}
                      </span>
                      <div className="text-right">
                        <span className="text-sm font-semibold text-slate-800">{temporal.measurement_count.toLocaleString()}</span>
                        <span className="text-xs text-slate-500 ml-2">({temporal.active_floats} floats)</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'rag' && (
            <div className="space-y-6">
              {/* RAG Capabilities */}
              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">RAG Search Capabilities</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {data.rag_insights.search_capabilities.map((capability, idx) => (
                    <div key={idx} className="flex items-start gap-3 p-3 bg-indigo-50 rounded-lg">
                      <div className="w-6 h-6 bg-indigo-500 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <span className="text-sm text-indigo-800">{capability}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Vector Quality */}
              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Vector Embeddings Quality</h3>
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
                  <p className="text-sm text-emerald-800">{data.rag_insights.vector_embeddings_quality}</p>
                </div>
              </div>

              {/* Sample Vector Content */}
              {data.rag_insights.sample_vector_content.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-xl p-6">
                  <h3 className="text-lg font-bold text-slate-800 mb-4">Sample Vector Content</h3>
                  <div className="space-y-3">
                    {data.rag_insights.sample_vector_content.map((sample, idx) => (
                      <div key={idx} className="p-3 bg-slate-50 rounded-lg">
                        <p className="text-xs font-mono text-slate-600 leading-relaxed">{sample}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* RAG Balance Test */}
              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-slate-800">RAG Pipeline Balance Test</h3>
                  <Button
                    onClick={testRAGBalance}
                    disabled={testingBalance}
                    variant="primary"
                    className="text-sm"
                  >
                    {testingBalance ? 'Testing...' : 'Run Balance Test'}
                  </Button>
                </div>
                
                {balanceTestResult && (
                  <div className="space-y-4">
                    <div className={`p-4 rounded-lg ${
                      balanceTestResult.overall_status === 'good' ? 'bg-emerald-50 border border-emerald-200' :
                      balanceTestResult.overall_status === 'needs_improvement' ? 'bg-amber-50 border border-amber-200' :
                      'bg-red-50 border border-red-200'
                    }`}>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold">Overall Status</h4>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                          balanceTestResult.overall_status === 'good' ? 'bg-emerald-100 text-emerald-700' :
                          balanceTestResult.overall_status === 'needs_improvement' ? 'bg-amber-100 text-amber-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {balanceTestResult.overall_status.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-sm">
                        Average context retrieval: {balanceTestResult.average_context_retrieval} results per query
                        • Available data points: {balanceTestResult.total_available_data.toLocaleString()}
                      </p>
                    </div>

                    {balanceTestResult.recommendations.length > 0 && (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <h4 className="font-semibold text-blue-800 mb-2">Recommendations</h4>
                        <ul className="space-y-1">
                          {balanceTestResult.recommendations.map((rec: string, idx: number) => (
                            <li key={idx} className="text-sm text-blue-700 flex items-start gap-2">
                              <span className="text-blue-500 mt-1">•</span>
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="space-y-2">
                      <h4 className="font-semibold text-slate-800">Test Query Results</h4>
                      {balanceTestResult.test_results.map((result: any, idx: number) => (
                        <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                          <div>
                            <p className="text-sm font-medium text-slate-800 truncate max-w-xs">
                              {result.query}
                            </p>
                            {result.error ? (
                              <p className="text-xs text-red-600">Error: {result.error}</p>
                            ) : (
                              <p className="text-xs text-slate-600">
                                Context: {result.vector_context_found} • Quality: {result.context_quality}
                              </p>
                            )}
                          </div>
                          <div className={`w-3 h-3 rounded-full ${
                            result.error ? 'bg-red-400' :
                            result.context_quality === 'good' ? 'bg-emerald-400' :
                            result.context_quality === 'limited' ? 'bg-amber-400' :
                            'bg-red-400'
                          }`}></div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {!balanceTestResult && !testingBalance && (
                  <p className="text-sm text-slate-600">
                    Test the RAG pipeline balance to identify potential data capture issues and optimization opportunities.
                  </p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'quality' && (
            <div className="space-y-6">
              {/* Quality Indicators */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className={`border rounded-xl p-6 ${getQualityColor(data.data_quality_indicators.completeness_score)}`}>
                  <div className="text-center">
                    <p className="text-sm font-semibold mb-2">Data Completeness</p>
                    <p className="text-3xl font-bold mb-1">{data.data_quality_indicators.completeness_score}%</p>
                    <p className="text-xs opacity-80">across all parameters</p>
                  </div>
                </div>

                <div className={`border rounded-xl p-6 ${getQualityColor(data.data_quality_indicators.vector_db_sync)}`}>
                  <div className="text-center">
                    <p className="text-sm font-semibold mb-2">Vector DB Sync</p>
                    <p className="text-3xl font-bold mb-1">{data.data_quality_indicators.vector_db_sync}%</p>
                    <p className="text-xs opacity-80">data synchronized</p>
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
                  <div className="text-center">
                    <p className="text-sm font-semibold text-blue-800 mb-2">Geographic Coverage</p>
                    <p className="text-3xl font-bold text-blue-900 mb-1">{data.data_quality_indicators.geographic_coverage}</p>
                    <p className="text-xs text-blue-600">distinct regions</p>
                  </div>
                </div>

                <div className="bg-violet-50 border border-violet-200 rounded-xl p-6">
                  <div className="text-center">
                    <p className="text-sm font-semibold text-violet-800 mb-2">Depth Coverage</p>
                    <p className="text-3xl font-bold text-violet-900 mb-1">{data.data_quality_indicators.depth_coverage}</p>
                    <p className="text-xs text-violet-600">depth categories</p>
                  </div>
                </div>
              </div>

              {/* Quality Insights */}
              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Quality Assessment</h3>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className={`w-4 h-4 rounded-full mt-1 ${
                      data.data_quality_indicators.completeness_score >= 90 ? 'bg-emerald-500' :
                      data.data_quality_indicators.completeness_score >= 70 ? 'bg-amber-500' : 'bg-red-500'
                    }`}></div>
                    <div>
                      <h4 className="font-semibold text-slate-800">Data Completeness</h4>
                      <p className="text-sm text-slate-600">
                        {data.data_quality_indicators.completeness_score >= 90 ? 'Excellent' :
                         data.data_quality_indicators.completeness_score >= 70 ? 'Good' : 'Needs Improvement'} - 
                        Temperature, salinity, and pressure measurements are {data.data_quality_indicators.completeness_score}% complete across all records.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <div className={`w-4 h-4 rounded-full mt-1 ${
                      data.data_quality_indicators.vector_db_sync >= 95 ? 'bg-emerald-500' :
                      data.data_quality_indicators.vector_db_sync >= 80 ? 'bg-amber-500' : 'bg-red-500'
                    }`}></div>
                    <div>
                      <h4 className="font-semibold text-slate-800">Vector Store Synchronization</h4>
                      <p className="text-sm text-slate-600">
                        {data.data_quality_indicators.vector_db_sync}% of database measurements have been vectorized and are available for semantic search.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <div className="w-4 h-4 rounded-full mt-1 bg-blue-500"></div>
                    <div>
                      <h4 className="font-semibold text-slate-800">Geographic Distribution</h4>
                      <p className="text-sm text-slate-600">
                        Data spans {data.data_quality_indicators.geographic_coverage} distinct oceanic regions, providing comprehensive geographic coverage for regional analysis.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <div className="w-4 h-4 rounded-full mt-1 bg-violet-500"></div>
                    <div>
                      <h4 className="font-semibold text-slate-800">Depth Coverage</h4>
                      <p className="text-sm text-slate-600">
                        Measurements cover {data.data_quality_indicators.depth_coverage} different depth categories from surface to abyssal depths.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};