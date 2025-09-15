import React, { useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default markers
delete ((L.Icon.Default as unknown) as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface MapPoint {
  lat: number;
  lon: number;
  float_id: string;
  temperature?: number;
  salinity?: number;
  depth?: number;
  date?: string;
}

interface OceanMapProps {
  points: MapPoint[];
  className?: string;
}

const OceanMap: React.FC<OceanMapProps> = ({ points, className = '' }) => {
  // Calculate bounds for auto-fit (memoized to prevent re-fitting on popup open)
  const bounds: [[number, number], [number, number]] = useMemo(() => {
    if (!points || points.length === 0) {
      return [[0, 0], [0, 0]];
    }
    const lats = points.map(d => d.lat);
    const lons = points.map(d => d.lon);
    return [
      [Math.min(...lats) - 1, Math.min(...lons) - 1],
      [Math.max(...lats) + 1, Math.max(...lons) + 1]
    ];
  }, [points]);

  if (!points || points.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <p className="text-gray-500 text-lg">No location data available for visualization</p>
      </div>
    );
  }

  // Enhanced temperature color mapping
  const getTemperatureColor = (temp?: number): string => {
    if (temp === undefined || temp === null) return '#6B7280'; // Gray for no data
    
    // Enhanced color scale from deep blue (cold) to red (hot)
    if (temp < 5) return '#1E3A8A';   // Deep blue
    if (temp < 10) return '#3B82F6';  // Blue
    if (temp < 15) return '#06B6D4';  // Cyan
    if (temp < 20) return '#10B981';  // Green
    if (temp < 25) return '#F59E0B';  // Amber
    if (temp < 30) return '#F97316';  // Orange
    return '#DC2626';                 // Red
  };

  // Enhanced marker size based on depth
  const getMarkerSize = (depth?: number): number => {
    if (depth === undefined || depth === null) return 8;
    
    // Larger markers for deeper measurements
    if (depth < 100) return 6;
    if (depth < 500) return 8;
    if (depth < 1000) return 10;
    return 12;
  };

  // Group points by unique location and float_id to avoid duplicate markers
  const uniqueLocations = points.reduce((acc, point) => {
    const key = `${point.lat}-${point.lon}-${point.float_id}`;
    if (!acc[key]) {
      // Find the surface measurement (smallest depth) for this location
      const surfacePoint = points
        .filter(p => p.lat === point.lat && p.lon === point.lon && p.float_id === point.float_id)
        .reduce((min, curr) => {
          const minDepth = (min.depth ?? Number.POSITIVE_INFINITY);
          const currDepth = (curr.depth ?? Number.POSITIVE_INFINITY);
          return currDepth < minDepth ? curr : min;
        }, point);
      acc[key] = surfacePoint;
    }
    return acc;
  }, {} as Record<string, MapPoint>);

  const uniquePoints = Object.values(uniqueLocations);

  return (
    <div className={`relative h-96 w-full rounded-lg shadow-lg ${className}`}>
      <MapContainer
        bounds={bounds}
        className="w-full h-full"
        style={{ minHeight: '384px' }}
        scrollWheelZoom={true}
        zoomControl={true}
      >
        {/* Enhanced satellite tile layer */}
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution='&copy; <a href="https://www.esri.com/">Esri</a> &mdash; Source: Esri, Maxar, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, and the GIS User Community'
        />
        
        {/* Ocean overlay for better context */}
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}"
          attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
          opacity={0.6}
        />

        {uniquePoints.map((point, index) => (
          <CircleMarker
            key={`${point.float_id}-${index}`}
            center={[point.lat, point.lon]}
            radius={getMarkerSize(point.depth)}
            fillColor={getTemperatureColor(point.temperature)}
            color="#FFFFFF"
            weight={2}
            opacity={0.9}
            fillOpacity={0.8}
            className="ocean-marker"
            eventHandlers={{
              mouseover: (e) => {
                const marker = e.target;
                marker.setStyle({
                  weight: 3,
                  opacity: 1,
                  fillOpacity: 1,
                  radius: getMarkerSize(point.depth) + 2
                });
              },
              mouseout: (e) => {
                const marker = e.target;
                marker.setStyle({
                  weight: 2,
                  opacity: 0.9,
                  fillOpacity: 0.8,
                  radius: getMarkerSize(point.depth)
                });
              }
            }}
          >
            <Popup
              className="custom-popup"
              maxWidth={280}
              closeButton={true}
              autoPan={true}
            >
              <div className="p-4 min-w-64 bg-white rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <div
                    className="w-4 h-4 rounded-full border-2 border-white"
                    style={{ backgroundColor: getTemperatureColor(point.temperature) }}
                  />
                  <div className="font-bold text-lg text-slate-800">
                    Float {point.float_id}
                  </div>
                </div>

                <div className="space-y-3 text-sm">
                  <div className="bg-gray-50 p-2 rounded-md">
                    <div className="flex justify-between items-center">
                      <span className="font-medium text-gray-600 flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        Location:
                      </span>
                      <span className="text-gray-800 font-mono text-xs">
                        {point.lat.toFixed(3)}°N, {point.lon.toFixed(3)}°E
                      </span>
                    </div>
                  </div>

                  {point.temperature !== undefined && point.temperature !== null && (
                    <div className="flex justify-between items-center border-l-4 border-red-400 pl-3">
                      <span className="font-medium text-gray-600 flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Temperature:
                      </span>
                      <span className="text-red-600 font-bold text-lg">
                        {point.temperature.toFixed(2)}°C
                      </span>
                    </div>
                  )}

                  {point.salinity !== undefined && point.salinity !== null && (
                    <div className="flex justify-between items-center border-l-4 border-blue-400 pl-3">
                      <span className="font-medium text-gray-600 flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                        </svg>
                        Salinity:
                      </span>
                      <span className="text-blue-600 font-bold text-lg">
                        {point.salinity.toFixed(3)} PSU
                      </span>
                    </div>
                  )}

                  {point.depth !== undefined && point.depth !== null && (
                    <div className="flex justify-between items-center border-l-4 border-indigo-400 pl-3">
                      <span className="font-medium text-gray-600 flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                        </svg>
                        Depth:
                      </span>
                      <span className="text-indigo-600 font-bold text-lg">
                        {point.depth.toFixed(1)}m
                      </span>
                    </div>
                  )}

                  {point.date && (
                    <div className="bg-gray-50 p-2 rounded-md">
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-gray-600 flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                          Date:
                        </span>
                        <span className="text-gray-800 font-medium">
                          {new Date(point.date).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric'
                          })}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      {/* Enhanced Temperature Legend */}
      <div className="absolute bottom-4 right-4 bg-white/95 backdrop-blur-sm p-4 rounded-lg shadow-lg border border-gray-200 pointer-events-none">
        <h4 className="font-bold text-sm text-gray-800 mb-3">Temperature Scale</h4>
        <div className="space-y-1">
          {[
            { temp: '<5°C', color: '#1E3A8A', label: 'Very Cold' },
            { temp: '5-10°C', color: '#3B82F6', label: 'Cold' },
            { temp: '10-15°C', color: '#06B6D4', label: 'Cool' },
            { temp: '15-20°C', color: '#10B981', label: 'Moderate' },
            { temp: '20-25°C', color: '#F59E0B', label: 'Warm' },
            { temp: '25-30°C', color: '#F97316', label: 'Hot' },
            { temp: '>30°C', color: '#DC2626', label: 'Very Hot' }
          ].map(({ temp, color, label }) => (
            <div key={temp} className="flex items-center gap-2 text-xs">
              <div 
                className="w-4 h-4 rounded-full border border-gray-300"
                style={{ backgroundColor: color }}
              />
              <span className="text-gray-700 font-medium">{temp}</span>
              <span className="text-gray-500">({label})</span>
            </div>
          ))}
        </div>
        
        <div className="mt-3 pt-2 border-t border-gray-200">
          <div className="text-xs text-gray-600">
            <div className="flex items-center gap-2 mb-1">
              <span>Marker size = depth</span>
            </div>
            <div>Total points: {points.length}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OceanMap;
