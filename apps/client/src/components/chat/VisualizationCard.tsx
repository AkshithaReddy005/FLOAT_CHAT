import React, { useState, useMemo } from 'react';
import OceanMap from '../visualization/OceanMap';
import DepthProfile from '../visualization/DepthProfile';
import CustomChart from '../visualization/CustomChart';
import { ResultsGrid } from '../researcher/ResultsGrid';
import type { ChatResponse, ArgoMeasurement } from '../../types';

interface VisualizationCardProps {
  chatResponse: ChatResponse;
  results: ArgoMeasurement[];
}

type TabType = 'data' | 'map' | 'profile' | 'custom';

export const VisualizationCard: React.FC<VisualizationCardProps> = ({
  chatResponse,
  results
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('data');
  const [isExpanded, setIsExpanded] = useState(false);

  // Transform data for visualizations
  const mapPoints = chatResponse?.visualization?.map?.points || [];
  const depthProfileData = chatResponse?.visualization?.depth_profile?.data || [];
  const customChart = chatResponse?.visualization?.custom_chart;
  const chartRequestInfo = chatResponse?.visualization?.chart_request_info;
  const vizReasoning = chatResponse?.visualization?.reasoning || '';
  const chartRecommendations = chatResponse?.visualization?.chart_recommendations || [];

  // Helper function to check if data is real/meaningful
  const isRealData = (data: ArgoMeasurement[]) => {
    return data.some(item => {
      // Check if data has real values (not all zeros/nulls)
      const hasRealCoords = item.latitude !== 0 && item.longitude !== 0 && 
                          item.latitude != null && item.longitude != null;
      const hasRealMeasurements = (item.temperature !== 0 && item.temperature != null) ||
                                (item.salinity !== 0 && item.salinity != null) ||
                                (item.depth !== 0 && item.depth != null);
      const hasRealFloatId = item.float_id && 
                           !item.float_id.includes('float_1') && 
                           !item.float_id.includes('000000') &&
                           item.float_id !== '';
      
      return hasRealCoords && hasRealMeasurements && hasRealFloatId;
    });
  };

  // Check if we have meaningful visualization data beyond just raw results
  // Custom charts should always be considered meaningful visualization data
  const hasVisualizationData = mapPoints.length > 0 || depthProfileData.length > 0 || !!customChart;
  
  // Only show if we have real data
  const hasRealResults = results.length > 0 && isRealData(results);

  // Determine which tabs to show based on available data
  const availableTabs = useMemo(
    () => ({
      custom: !!customChart,
      data: hasRealResults, // Only show data tab if we have real, meaningful results
      map: mapPoints.length > 0 && hasRealResults,
      profile: depthProfileData.length > 0 && hasRealResults
    }),
    [customChart, hasRealResults, mapPoints.length, depthProfileData.length]
  );

  // Set default active tab to first available (prioritize custom charts)
  React.useEffect(() => {
    if (!availableTabs[activeTab]) {
      if (availableTabs.custom) setActiveTab('custom');
      else if (availableTabs.data) setActiveTab('data');
      else if (availableTabs.map) setActiveTab('map');
      else if (availableTabs.profile) setActiveTab('profile');
    }
  }, [availableTabs, activeTab]);

  // Don't render if no meaningful visualization data OR no real data is available
  if (!hasVisualizationData && !hasRealResults) {
    return null;
  }
  
  // Don't render if we only have fake/sample data
  if (results.length > 0 && !isRealData(results) && !customChart) {
    return null;
  }

  const getTabIcon = (tab: TabType) => {
    switch (tab) {
      case 'custom':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
        );
      case 'data':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5a2 2 0 012-2h4a2 2 0 012 2v0" />
          </svg>
        );
      case 'map':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
        );
      case 'profile':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        );
      default:
        return null;
    }
  };

  const getTabLabel = (tab: TabType) => {
    switch (tab) {
      case 'custom':
        return `Custom Chart`;
      case 'data':
        return `Data (${results.length})`;
      case 'map':
        return `Map (${mapPoints.length})`;
      case 'profile':
        return `Profiles (${depthProfileData.length})`;
      default:
        return '';
    }
  };

  return (
    <div className="mt-4 bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-emerald-50 px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-lg flex items-center justify-center">
              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
              </svg>
            </div>
            <h3 className="text-sm font-semibold text-gray-800">Data Visualization</h3>
          </div>
          
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center space-x-1 transition-colors"
          >
            <span>{isExpanded ? 'Collapse' : 'Expand'}</span>
            <svg 
              className={`w-4 h-4 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

        {/* Visualization Reasoning */}
        {vizReasoning && (
          <div className="mt-3 mb-2">
            <div className="flex items-start space-x-2 text-xs">
              <div className="flex-shrink-0 mt-0.5">
                <svg className="w-3 h-3 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="text-gray-600 flex-1">
                <span className="font-medium text-blue-700">Chart Selection:</span> {vizReasoning}
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="mt-3 flex space-x-1 overflow-x-auto">
          {Object.entries(availableTabs).map(([tab, available]) => {
            if (!available) return null;
            
            const tabType = tab as TabType;
            const isActive = activeTab === tabType;
            
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tabType)}
                className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800 hover:bg-white/50'
                }`}
              >
                {getTabIcon(tabType)}
                <span>{getTabLabel(tabType)}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className={`transition-all duration-300 overflow-hidden ${
        isExpanded ? 'max-h-none' : 'max-h-0'
      }`}>
        <div className="p-4 max-h-[800px] overflow-y-auto overflow-x-auto">
          {activeTab === 'custom' && availableTabs.custom && customChart && (
            <div>
              <div className="mb-3">
                <h4 className="text-sm font-semibold text-gray-800 mb-1">
                  Custom Chart
                </h4>
                <p className="text-xs text-gray-600">
                  AI-generated chart based on your request
                  {chartRequestInfo?.explanation && (
                    <span className="ml-2 text-blue-600">• {chartRequestInfo.explanation}</span>
                  )}
                </p>
              </div>
              <CustomChart 
                chartConfig={{
                  data: customChart.data || [],
                  layout: customChart.layout || {},
                  config: customChart.config || {}
                }}
                chartRequestInfo={chartRequestInfo ? {
                  title: chartRequestInfo.title || customChart.title || 'Custom Chart',
                  explanation: chartRequestInfo.explanation || '',
                  chart_type: chartRequestInfo.chart_type || 'line',
                  x_axis: chartRequestInfo.x_axis || 'X Axis',
                  y_axis: chartRequestInfo.y_axis || 'Y Axis'
                } : undefined}
              />
            </div>
          )}

          {activeTab === 'data' && availableTabs.data && (
            <div className="overflow-x-auto">
              <ResultsGrid results={results} />
            </div>
          )}
          
          {activeTab === 'map' && availableTabs.map && (
            <div>
              <div className="mb-3">
                <h4 className="text-sm font-semibold text-gray-800 mb-1">
                  ARGO Float Locations
                </h4>
                <p className="text-xs text-gray-600">
                  Interactive map showing {mapPoints.length} data points
                  {chatResponse?.visualization?.map?.reason && (
                    <span className="ml-2 text-blue-600">• {chatResponse.visualization.map.reason}</span>
                  )}
                </p>
                {chatResponse?.visualization?.map?.recommended_type && (
                  <div className="mt-1 text-xs text-gray-500 flex items-center space-x-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    <span>Optimized as {chatResponse.visualization.map.recommended_type.replace(/_/g, ' ')}</span>
                  </div>
                )}
              </div>
              <div className="rounded-lg overflow-hidden border border-gray-200">
                <OceanMap points={mapPoints} />
              </div>
            </div>
          )}
          
          {activeTab === 'profile' && availableTabs.profile && (
            <div>
              <div className="mb-3">
                <h4 className="text-sm font-semibold text-gray-800 mb-1">
                  Temperature and Salinity Profiles
                </h4>
                <p className="text-xs text-gray-600">
                  Depth profiles from {depthProfileData.length} measurements
                  {chatResponse?.visualization?.depth_profile?.depth_range && (
                    <span className="ml-2 text-blue-600">
                      • {chatResponse.visualization.depth_profile.depth_range.min}m to {chatResponse.visualization.depth_profile.depth_range.max}m depth
                    </span>
                  )}
                </p>
                {chartRecommendations?.find((r: { type: string; reason: string }) => r.type === 'depth_profile')?.reason && (
                  <div className="mt-1 text-xs text-gray-500 flex items-center space-x-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                    <span>{chartRecommendations.find((r: { type: string; reason: string }) => r.type === 'depth_profile')?.reason}</span>
                  </div>
                )}
              </div>
              <div className="rounded-lg overflow-hidden border border-gray-200">
                <DepthProfile data={depthProfileData} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Quick Stats Footer */}
      <div className="bg-gray-50 px-4 py-2 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <div className="flex items-center space-x-4">
            {results.length > 0 && (
              <span className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <span>{results.length} records</span>
              </span>
            )}
            {mapPoints.length > 0 && (
              <span className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                <span>{mapPoints.length} locations</span>
              </span>
            )}
            {customChart && (
              <span className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                <span>custom chart</span>
              </span>
            )}
            {depthProfileData.length > 0 && (
              <span className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                <span>{depthProfileData.length} profiles</span>
              </span>
            )}
          </div>
          <div className="text-gray-500">
            {chatResponse.context_count > 0 && `${chatResponse.context_count} context items`}
          </div>
        </div>
      </div>
    </div>
  );
};