import React, { useState, useEffect } from 'react';
import { X, RefreshCw, Waves, MapPin, ThermometerSun, Droplet, Gauge, Calendar, TrendingUp, Globe } from 'lucide-react';
import { apiService } from '../../services/api';

interface AnalyticsData {
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
    min_depth: number;
    max_depth: number;
    avg_depth: number;
  }>;
  geographic_distribution: Array<{
    region: string;
    measurement_count: number;
    float_count: number;
    lat_range: [number, number];
    lon_range: [number, number];
  }>;
  parameter_coverage: {
    total_measurements: number;
    temperature_coverage: number;
    salinity_coverage: number;
    pressure_coverage: number;
    ranges: {
      temperature: {
        avg: number;
        min: number;
        max: number;
      };
      salinity: {
        avg: number;
        min: number;
        max: number;
      };
    };
  };
  temporal_distribution: Array<{
    month: string;
    measurement_count: number;
    active_floats: number;
  }>;
  data_quality_indicators: {
    completeness_score: number;
    geographic_coverage: number;
    depth_coverage: number;
    vector_db_sync: number;
  };
}

interface UserAnalyticsProps {
  onClose: () => void;
}

export const UserAnalytics: React.FC<UserAnalyticsProps> = ({ onClose }) => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAnalyticsData = async () => {
    setLoading(true);
    setError(null);
    try {
      const analyticsData = await apiService.getKnowledgeBaseDetails();
      setData(analyticsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalyticsData();
  }, []);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl max-w-4xl w-full mx-4 h-[80vh] flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-600">Loading analytics data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl max-w-md w-full mx-4 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">Analytics Unavailable</h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
              <X className="w-6 h-6" />
            </button>
          </div>
          <div className="text-center py-8">
            <p className="text-gray-600 mb-4">{error}</p>
            <button
              onClick={loadAnalyticsData}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl max-w-md w-full mx-4 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">No Data Available</h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
              <X className="w-6 h-6" />
            </button>
          </div>
          <div className="text-center py-8">
            <p className="text-gray-600">No analytics data is currently available.</p>
          </div>
        </div>
      </div>
    );
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toLocaleString();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-6xl w-full h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-xl flex items-center justify-center">
              <Waves className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-800">Ocean Data Analytics</h2>
              <p className="text-sm text-gray-600">Comprehensive insights into ARGO float measurements</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={loadAnalyticsData}
              disabled={loading}
              className="flex items-center space-x-1 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
                  <Waves className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-blue-800">Total Measurements</p>
                  <p className="text-2xl font-bold text-blue-900">{formatNumber(data.knowledge_base_overview.database_measurements)}</p>
                  <p className="text-xs text-blue-600">oceanographic data points</p>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-r from-emerald-50 to-green-50 border border-emerald-200 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-500 rounded-lg flex items-center justify-center">
                  <Globe className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-emerald-800">ARGO Instruments</p>
                  <p className="text-2xl font-bold text-emerald-900">{formatNumber(data.knowledge_base_overview.unique_instruments)}</p>
                  <p className="text-xs text-emerald-600">active float profiles</p>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-r from-purple-50 to-violet-50 border border-purple-200 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center">
                  <MapPin className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-purple-800">Geographic Coverage</p>
                  <p className="text-2xl font-bold text-purple-900">{data.data_quality_indicators.geographic_coverage}</p>
                  <p className="text-xs text-purple-600">distinct regions</p>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-amber-500 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-amber-800">Data Quality</p>
                  <p className="text-2xl font-bold text-amber-900">{data.data_quality_indicators.completeness_score.toFixed(1)}%</p>
                  <p className="text-xs text-amber-600">completeness score</p>
                </div>
              </div>
            </div>
          </div>

          {/* Regional Distribution */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <MapPin className="w-5 h-5 text-blue-500" />
              Regional Distribution
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.geographic_distribution.map((region, index) => (
                <div key={index} className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-semibold text-gray-800 mb-2">{region.region}</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Measurements:</span>
                      <span className="font-medium">{formatNumber(region.measurement_count)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Floats:</span>
                      <span className="font-medium">{region.float_count}</span>
                    </div>
                    {region.lat_range && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Latitude:</span>
                        <span className="font-medium">{region.lat_range[0].toFixed(1)}° to {region.lat_range[1].toFixed(1)}°</span>
                      </div>
                    )}
                    {region.lon_range && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Longitude:</span>
                        <span className="font-medium">{region.lon_range[0].toFixed(1)}° to {region.lon_range[1].toFixed(1)}°</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Depth Distribution */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Gauge className="w-5 h-5 text-blue-500" />
              Depth Distribution
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              {data.depth_distribution.map((depth, index) => (
                <div key={index} className="bg-gradient-to-b from-blue-50 to-blue-100 rounded-lg p-4">
                  <h4 className="font-semibold text-blue-800 mb-2 capitalize">{depth.category}</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-blue-600">Count:</span>
                      <span className="font-medium text-blue-800">{formatNumber(depth.count)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-blue-600">Avg Depth:</span>
                      <span className="font-medium text-blue-800">{depth.avg_depth?.toFixed(0)}m</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-blue-600">Range:</span>
                      <span className="font-medium text-blue-800">{depth.min_depth?.toFixed(0)}-{depth.max_depth?.toFixed(0)}m</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Parameter Coverage */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <ThermometerSun className="w-5 h-5 text-red-500" />
                Temperature Analysis
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Coverage:</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-red-500 h-2 rounded-full"
                        style={{ width: `${data.parameter_coverage.temperature_coverage}%` }}
                      ></div>
                    </div>
                    <span className="font-medium">{data.parameter_coverage.temperature_coverage.toFixed(1)}%</span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="bg-red-50 rounded-lg p-3">
                    <p className="text-xs text-red-600">Average</p>
                    <p className="font-bold text-red-800">{data.parameter_coverage.ranges.temperature.avg?.toFixed(1)}°C</p>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-3">
                    <p className="text-xs text-blue-600">Minimum</p>
                    <p className="font-bold text-blue-800">{data.parameter_coverage.ranges.temperature.min?.toFixed(1)}°C</p>
                  </div>
                  <div className="bg-orange-50 rounded-lg p-3">
                    <p className="text-xs text-orange-600">Maximum</p>
                    <p className="font-bold text-orange-800">{data.parameter_coverage.ranges.temperature.max?.toFixed(1)}°C</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <Droplet className="w-5 h-5 text-blue-500" />
                Salinity Analysis
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Coverage:</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${data.parameter_coverage.salinity_coverage}%` }}
                      ></div>
                    </div>
                    <span className="font-medium">{data.parameter_coverage.salinity_coverage.toFixed(1)}%</span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="bg-blue-50 rounded-lg p-3">
                    <p className="text-xs text-blue-600">Average</p>
                    <p className="font-bold text-blue-800">{data.parameter_coverage.ranges.salinity.avg?.toFixed(2)} PSU</p>
                  </div>
                  <div className="bg-cyan-50 rounded-lg p-3">
                    <p className="text-xs text-cyan-600">Minimum</p>
                    <p className="font-bold text-cyan-800">{data.parameter_coverage.ranges.salinity.min?.toFixed(2)} PSU</p>
                  </div>
                  <div className="bg-indigo-50 rounded-lg p-3">
                    <p className="text-xs text-indigo-600">Maximum</p>
                    <p className="font-bold text-indigo-800">{data.parameter_coverage.ranges.salinity.max?.toFixed(2)} PSU</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-green-500" />
              Recent Measurement Activity
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.temporal_distribution.slice(0, 6).map((period, index) => (
                <div key={index} className="bg-green-50 rounded-lg p-4">
                  <h4 className="font-semibold text-green-800 mb-2">
                    {new Date(period.month).toLocaleDateString('en-US', { year: 'numeric', month: 'long' })}
                  </h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-green-600">Measurements:</span>
                      <span className="font-medium text-green-800">{formatNumber(period.measurement_count)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-green-600">Active Floats:</span>
                      <span className="font-medium text-green-800">{period.active_floats}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};