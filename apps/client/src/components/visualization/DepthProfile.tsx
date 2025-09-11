import React from 'react';
import Plot from 'react-plotly.js';

interface DepthProfileData {
  depth: number;
  temperature: number;
  salinity: number;
  float_id: string;
}

interface DepthProfileProps {
  data: DepthProfileData[];
  className?: string;
}

const DepthProfile: React.FC<DepthProfileProps> = ({ data, className = '' }) => {
  // Group data by float_id
  const groupedData = data.reduce((acc, point) => {
    if (!acc[point.float_id]) {
      acc[point.float_id] = [];
    }
    acc[point.float_id].push(point);
    return acc;
  }, {} as Record<string, DepthProfileData[]>);

  // Sort each float's data by depth
  Object.values(groupedData).forEach(floatData => {
    floatData.sort((a, b) => a.depth - b.depth);
  });

  const floatIds = Object.keys(groupedData);
  const colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'];

  // Debug logging
  console.log('Depth Profile Debug:', {
    totalDataPoints: data.length,
    uniqueFloats: floatIds,
    dataPerFloat: Object.fromEntries(
      floatIds.map(id => [id, groupedData[id].length])
    ),
    depthRanges: Object.fromEntries(
      floatIds.map(id => [
        id, 
        {
          min: Math.min(...groupedData[id].map(d => d.depth)),
          max: Math.max(...groupedData[id].map(d => d.depth))
        }
      ])
    )
  });

  // Create temperature traces
  const temperatureTraces = floatIds.map((floatId, index) => ({
    x: groupedData[floatId].map(d => d.temperature),
    y: groupedData[floatId].map(d => -d.depth), // Negative for oceanographic convention
    mode: 'lines+markers' as const,
    name: `${floatId} Temperature`,
    line: { color: colors[index % colors.length], width: 2 },
    marker: { size: 4 },
    xaxis: 'x',
    yaxis: 'y',
    legendgroup: floatId,
    hovertemplate: '<b>%{fullData.name}</b><br>' +
                  'Temperature: %{x:.1f}°C<br>' +
                  'Depth: %{customdata:.0f}m<br>' +
                  '<extra></extra>',
    customdata: groupedData[floatId].map(d => d.depth),
  }));

  // Create salinity traces
  const salinityTraces = floatIds.map((floatId, index) => ({
    x: groupedData[floatId].map(d => d.salinity),
    y: groupedData[floatId].map(d => -d.depth), // Negative for oceanographic convention
    mode: 'lines+markers' as const,
    name: `${floatId} Salinity`,
    line: { color: colors[index % colors.length], width: 2, dash: 'dash' },
    marker: { size: 4, symbol: 'square' },
    xaxis: 'x2',
    yaxis: 'y',
    legendgroup: floatId,
    hovertemplate: '<b>%{fullData.name}</b><br>' +
                  'Salinity: %{x:.2f} PSU<br>' +
                  'Depth: %{customdata:.0f}m<br>' +
                  '<extra></extra>',
    customdata: groupedData[floatId].map(d => d.depth),
  }));

  const allTraces = [...temperatureTraces, ...salinityTraces];

  const layout = {
    title: {
      text: `Ocean Depth Profiles (${floatIds.length} ARGO Floats)`,
      font: { size: 18, color: '#1f2937' }
    },
    xaxis: {
      title: { text: 'Temperature (°C)' },
      domain: [0, 0.45],
      showgrid: true,
      gridcolor: '#e5e7eb',
      color: '#374151'
    },
    xaxis2: {
      title: { text: 'Salinity (PSU)' },
      domain: [0.55, 1],
      showgrid: true,
      gridcolor: '#e5e7eb',
      color: '#374151'
    },
    yaxis: {
      title: { text: 'Depth (m)' },
      autorange: 'reversed' as const,
      showgrid: true,
      gridcolor: '#e5e7eb',
      color: '#374151'
    },
    legend: {
      x: 1.02,
      y: 1,
      bgcolor: 'rgba(255,255,255,0.8)',
      bordercolor: '#d1d5db',
      borderwidth: 1,
      tracegroupgap: 10
    },
    margin: { l: 60, r: 150, t: 60, b: 60 },
    plot_bgcolor: '#f9fafb',
    paper_bgcolor: 'white',
    hovermode: 'closest' as const,
    showlegend: true
  };

  const config = {
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'] as any,
    displaylogo: false
  };

  return (
    <div className={`w-full bg-white rounded-lg shadow-lg p-4 ${className}`}>
      <Plot
        data={allTraces}
        layout={layout}
        config={config}
        style={{ width: '100%', height: '500px' }}
      />
      <div className="mt-4 text-sm text-gray-600">
        <p><strong>Note:</strong> Solid lines represent temperature profiles, dashed lines represent salinity profiles.</p>
        <p>Depth follows oceanographic convention (surface = 0m, deeper = negative values).</p>
        <p><strong>Data Summary:</strong> {data.length} measurements from {floatIds.length} ARGO floats: {floatIds.join(', ')}</p>
      </div>
    </div>
  );
};

export default DepthProfile;
