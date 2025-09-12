import React from 'react';
import Plot from 'react-plotly.js';

interface DepthProfileData {
  depth: number;
  temperature: number;
  salinity: number;
  float_id: string;
}

interface AggregatedDepthProfileData {
  depth: number;
  count: number;
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
  pressure: {
    avg: number | null;
    min: number | null;
    max: number | null;
  };
}

interface DepthProfileProps {
  data: DepthProfileData[] | AggregatedDepthProfileData[];
  className?: string;
}

const DepthProfile: React.FC<DepthProfileProps> = ({ data, className = '' }) => {
  // Check if data is aggregated format (has 'count' property) or individual measurements
  const isAggregatedData = data.length > 0 && 'count' in data[0];
  
  let groupedData: Record<string, DepthProfileData[]>;
  
  if (isAggregatedData) {
    // Transform aggregated data to individual format for visualization
    const aggregatedData = data as AggregatedDepthProfileData[];
    const transformedData: DepthProfileData[] = [];
    
    aggregatedData.forEach(point => {
      if (point.temperature.avg !== null && point.salinity.avg !== null) {
        transformedData.push({
          depth: point.depth,
          temperature: point.temperature.avg,
          salinity: point.salinity.avg,
          float_id: `Depth-${point.depth}m` // Use depth as identifier for aggregated data
        });
      }
    });
    
    // Group by single aggregated profile
    groupedData = { 'Aggregated Profile': transformedData };
  } else {
    // Group individual measurement data by float_id
    const individualData = data as DepthProfileData[];
    groupedData = individualData.reduce((acc, point) => {
      if (!acc[point.float_id]) {
        acc[point.float_id] = [];
      }
      acc[point.float_id].push(point);
      return acc;
    }, {} as Record<string, DepthProfileData[]>);
  }

  // Sort each float's data by depth
  Object.values(groupedData).forEach(floatData => {
    floatData.sort((a, b) => a.depth - b.depth);
  });

  const floatIds = Object.keys(groupedData);
  const colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'];

  // Create temperature traces
  const temperatureTraces = floatIds.map((floatId, index) => ({
    x: groupedData[floatId].map(d => d.temperature),
    y: groupedData[floatId].map(d => -d.depth), // Negative for oceanographic convention
    mode: 'lines+markers' as const,
    name: `${floatId} Temperature`,
    line: { color: colors[index % colors.length], width: 3 },
    marker: { size: 6, line: { width: 1, color: 'white' } },
    xaxis: 'x',
    yaxis: 'y',
    legendgroup: floatId,
    hovertemplate: '<b>Temperature</b><br>' +
                  'Value: <b>%{x:.2f}°C</b><br>' +
                  'Depth: <b>%{customdata:.0f}m</b><br>' +
                  'Float: <b>' + floatId + '</b><br>' +
                  '<extra></extra>',
    customdata: groupedData[floatId].map(d => d.depth)
  }));

  // Create salinity traces
  const salinityTraces = floatIds.map((floatId, index) => ({
    x: groupedData[floatId].map(d => d.salinity),
    y: groupedData[floatId].map(d => -d.depth), // Negative for oceanographic convention
    mode: 'lines+markers' as const,
    name: `${floatId} Salinity`,
    line: { color: colors[index % colors.length], width: 3, dash: 'dash' },
    marker: { size: 6, symbol: 'square', line: { width: 1, color: 'white' } },
    xaxis: 'x2',
    yaxis: 'y',
    legendgroup: floatId,
    hovertemplate: '<b>Salinity</b><br>' +
                  'Value: <b>%{x:.3f} PSU</b><br>' +
                  'Depth: <b>%{customdata:.0f}m</b><br>' +
                  'Float: <b>' + floatId + '</b><br>' +
                  '<extra></extra>',
    customdata: groupedData[floatId].map(d => d.depth)
  }));

  const allTraces = [...temperatureTraces, ...salinityTraces];

  const layout = {
    title: {
      text: `Ocean Depth Profiles (${floatIds.length} ARGO Floats)`,
      font: { size: 18, color: '#1f2937' },
      x: 0.05
    },
    xaxis: {
      title: { 
        text: 'Temperature (°C)', 
        font: { size: 14, color: '#374151' },
        standoff: 20
      },
      domain: [0, 0.42],
      showgrid: true,
      gridcolor: '#e5e7eb',
      gridwidth: 1,
      color: '#374151',
      tickfont: { size: 12 },
      zeroline: false
    },
    xaxis2: {
      title: { 
        text: 'Salinity (PSU)', 
        font: { size: 14, color: '#374151' },
        standoff: 20
      },
      domain: [0.58, 1],
      showgrid: true,
      gridcolor: '#e5e7eb',
      gridwidth: 1,
      color: '#374151',
      tickfont: { size: 12 },
      zeroline: false
    },
    yaxis: {
      title: { 
        text: 'Depth (m)', 
        font: { size: 14, color: '#374151' },
        standoff: 25
      },
      autorange: 'reversed' as const,
      showgrid: true,
      gridcolor: '#e5e7eb',
      gridwidth: 1,
      color: '#374151',
      tickfont: { size: 12 },
      zeroline: false
    },
    legend: {
      x: 1.02,
      y: 1,
      bgcolor: 'rgba(255,255,255,0.95)',
      bordercolor: '#d1d5db',
      borderwidth: 1,
      tracegroupgap: 8,
      font: { size: 11 }
    },
    margin: { l: 80, r: 160, t: 80, b: 80 },
    plot_bgcolor: '#fafbfc',
    paper_bgcolor: 'white',
    hovermode: 'closest' as const,
    showlegend: true,
    hoverlabel: {
      bgcolor: 'rgba(255,255,255,0.95)',
      bordercolor: '#374151',
      borderwidth: 1,
      font: { 
        size: 12,
        color: '#1f2937'
      }
    },
    height: 700
  };

  const config = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    toImageButtonOptions: {
      format: 'png' as const,
      filename: 'depth_profile',
      height: 700,
      width: 1200,
      scale: 1
    },
    scrollZoom: true
  };

  return (
    <div className={`w-full bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden ${className}`}>
      <div className="p-6">
        <Plot
          data={allTraces}
          layout={layout}
          config={config}
          style={{ width: '100%', height: '700px' }}
          useResizeHandler={true}
        />
      </div>
      <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700">
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-0.5 bg-blue-500"></div>
              <span><strong>Temperature profiles:</strong> Solid lines with circles</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-0.5 bg-blue-500 border-dashed border-t-2 border-blue-500"></div>
              <span><strong>Salinity profiles:</strong> Dashed lines with squares</span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <span className="text-blue-600 font-bold">•</span>
              <span><strong>Data points:</strong> {data.length} measurements</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-emerald-600 font-bold">•</span>
              <span><strong>ARGO floats:</strong> {floatIds.length} float{floatIds.length !== 1 ? 's' : ''}</span>
            </div>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-gray-300">
          <p className="text-xs text-gray-600">
            <strong>Tip:</strong> Hover over data points for detailed information. Use zoom and pan controls for better exploration.
          </p>
        </div>
      </div>
    </div>
  );
};

export default DepthProfile;
