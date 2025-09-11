import React, { useState } from 'react';
import OceanMap from '../visualization/OceanMap';
import DepthProfile from '../visualization/DepthProfile';
import { ResultsGrid } from '../researcher/ResultsGrid';
import type { ChatResponse, ArgoMeasurement } from '../../types';

interface VisualizationCardProps {
  chatResponse: ChatResponse;
  results: ArgoMeasurement[];
}

type TabType = 'data' | 'map' | 'profile';

export const VisualizationCard: React.FC<VisualizationCardProps> = ({
  chatResponse,
  results
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('data');
  const [isExpanded, setIsExpanded] = useState(false);

  // Transform data for visualizations
  const mapPoints = chatResponse?.visualization?.map?.points || [];
  const depthProfileData = chatResponse?.visualization?.depth_profile?.data || [];

  // Determine which tabs to show based on available data
  const availableTabs = {
    data: results.length > 0,
    map: mapPoints.length > 0,
    profile: depthProfileData.length > 0
  };

  // Set default active tab to first available
  React.useEffect(() => {
    if (!availableTabs[activeTab]) {
      if (availableTabs.data) setActiveTab('data');
      else if (availableTabs.map) setActiveTab('map');
      else if (availableTabs.profile) setActiveTab('profile');
    }
  }, [availableTabs, activeTab]);

  // Don't render if no data to visualize
  if (!availableTabs.data && !availableTabs.map && !availableTabs.profile) {
    return null;
  }

  const getTabIcon = (tab: TabType) => {
    switch (tab) {
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
            className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center space-x-1"
          >
            <span>{isExpanded ? 'Collapse' : 'Expand'}</span>
            <svg 
              className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

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
        isExpanded ? 'max-h-[800px]' : 'max-h-[400px]'
      }`}>
        <div className="p-4">
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
                </p>
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
                </p>
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