import { useState } from 'react';
import { Layout } from '../common/Layout';
import { SearchInput } from './SearchInput';
import { ResultsGrid } from './ResultsGrid';
import OceanMap from '../visualization/OceanMap';
import DepthProfile from '../visualization/DepthProfile';
import { useQuery } from '../../hooks/useQuery';
import { formatChatMessage } from '../../utils/formatChatMessage';

export const ResearcherDashboard = () => {
  const [query, setQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'data' | 'map' | 'profile'>('data');
  const { results, isLoading, message, chatResponse, queryData } = useQuery();

  const handleSearch = () => {
    queryData(query);
  };

  // Transform data for map visualization
  const mapPoints = chatResponse?.visualization?.map?.points || [];

  // Transform data for depth profile
  const depthProfileData = chatResponse?.visualization?.depth_profile?.data || [];

  return (
    <Layout title="Research Portal">
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Research Portal</h1>
        </div>
        
        <SearchInput
          query={query}
          onQueryChange={setQuery}
          onSearch={handleSearch}
          isLoading={isLoading}
        />
        
        {/* Chat Response Message */}
        {message && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">Analysis Results</h3>
            <p className="text-blue-800" dangerouslySetInnerHTML={{ __html: formatChatMessage(message) }} />
          </div>
        )}

        {/* Visualization Tabs */}
        {results.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg">
            <div className="border-b border-gray-200">
              <nav className="flex space-x-8 px-6">
                <button
                  onClick={() => setActiveTab('data')}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'data'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Data Table ({results.length})
                </button>
                <button
                  onClick={() => setActiveTab('map')}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'map'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Interactive Map
                </button>
                <button
                  onClick={() => setActiveTab('profile')}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'profile'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Depth Profiles
                </button>
              </nav>
            </div>

            <div className="p-6">
              {activeTab === 'data' && <ResultsGrid results={results} query={query} />}
              
              {activeTab === 'map' && (
                <div>
                  <h3 className="text-lg font-semibold mb-4 text-gray-900">
                    ARGO Float Locations
                  </h3>
                  {mapPoints.length > 0 ? (
                    <OceanMap points={mapPoints} />
                  ) : (
                    <div className="text-center py-12 text-gray-500">
                      <p>No location data available for visualization</p>
                    </div>
                  )}
                </div>
              )}
              
              {activeTab === 'profile' && (
                <div>
                  <h3 className="text-lg font-semibold mb-4 text-gray-900">
                    Temperature and Salinity Profiles
                  </h3>
                  {depthProfileData.length > 0 ? (
                    <DepthProfile data={depthProfileData} />
                  ) : (
                    <div className="text-center py-12 text-gray-500">
                      <p>No depth profile data available for visualization</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* No global export button per user request */}
      </div>
    </Layout>
  );
};