import React from 'react';
import { MapContainer, TileLayer, CircleMarker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default markers
delete (L.Icon.Default.prototype as any)._getIconUrl;
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
  if (!points || points.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <p className="text-gray-500 text-lg">No location data available for visualization</p>
      </div>
    );
  }

  // Calculate bounds for auto-fit
  const lats = points.map(d => d.lat);
  const lons = points.map(d => d.lon);
  const bounds: [[number, number], [number, number]] = [
    [Math.min(...lats) - 1, Math.min(...lons) - 1],
    [Math.max(...lats) + 1, Math.max(...lons) + 1]
  ];

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
        .reduce((min, curr) => curr.depth < min.depth ? curr : min, point);
      acc[key] = surfacePoint;
    }
    return acc;
  }, {} as Record<string, MapPoint>);

  const uniquePoints = Object.values(uniqueLocations);

  return (
    <div className={`h-96 w-full rounded-lg overflow-hidden shadow-lg ${className}`}>
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
            className="hover:scale-110 transition-transform duration-200"
          >
            <Popup className="custom-popup">
              <div className="p-3 min-w-48">
                <div className="font-bold text-lg text-blue-800 mb-2">
                  Float {point.float_id}
                </div>
                
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="font-medium text-gray-600">Location:</span>
                    <span className="text-gray-800">
                      {point.lat.toFixed(3)}°, {point.lon.toFixed(3)}°
                    </span>
                  </div>
                  
                  {point.temperature !== undefined && point.temperature !== null && (
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600">Temperature:</span>
                      <span className="text-red-600 font-semibold">
                        {point.temperature.toFixed(2)}°C
                      </span>
                    </div>
                  )}
                  
                  {point.salinity !== undefined && point.salinity !== null && (
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600">Salinity:</span>
                      <span className="text-blue-600 font-semibold">
                        {point.salinity.toFixed(2)}
                      </span>
                    </div>
                  )}
                  
                  {point.depth !== undefined && point.depth !== null && (
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600">Depth:</span>
                      <span className="text-indigo-600 font-semibold">
                        {point.depth.toFixed(1)}m
                      </span>
                    </div>
                  )}
                  
                  {point.date && (
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600">Date:</span>
                      <span className="text-gray-800">
                        {new Date(point.date).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      {/* Enhanced Temperature Legend */}
      <div className="absolute bottom-4 right-4 bg-white/95 backdrop-blur-sm p-4 rounded-lg shadow-lg border border-gray-200">
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
