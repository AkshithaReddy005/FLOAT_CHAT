import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';

interface CustomChartProps {
  chartConfig: {
    data: Record<string, unknown>[];
    layout: Record<string, unknown>;
    config?: Record<string, unknown>;
  };
  chartRequestInfo?: {
    title: string;
    explanation: string;
    chart_type: string;
    x_axis: string;
    y_axis: string;
  };
  className?: string;
}

const CustomChart: React.FC<CustomChartProps> = ({ 
  chartConfig, 
  chartRequestInfo, 
  className = '' 
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Simulate loading state for better UX
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 100);
    return () => clearTimeout(timer);
  }, [chartConfig]);
  // Validate and sanitize chart data
  const isValidData = chartConfig && 
    chartConfig.data && 
    Array.isArray(chartConfig.data) && 
    chartConfig.data.length > 0 &&
    chartConfig.data.every(trace => trace && typeof trace === 'object') &&
    // Ensure at least one trace has valid data arrays
    chartConfig.data.some(trace => 
      (trace.x && Array.isArray(trace.x) && trace.x.length > 0) ||
      (trace.y && Array.isArray(trace.y) && trace.y.length > 0)
    );

  if (!isValidData) {
    return (
      <div className={`w-full bg-white rounded-lg shadow-lg p-6 ${className}`}>
        <div className="text-center text-gray-500">
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Chart Data</h3>
          <p className="text-sm text-gray-600">Unable to generate chart with the provided configuration.</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={`w-full bg-white rounded-lg shadow-lg p-6 ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-sm text-gray-600">Loading chart...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`w-full bg-white rounded-lg shadow-lg p-6 ${className}`}>
        <div className="text-center text-red-500">
          <svg className="w-16 h-16 mx-auto mb-4 text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="text-lg font-medium text-red-900 mb-2">Chart Error</h3>
          <p className="text-sm text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  // Sanitize chart data to prevent null/undefined errors
  const sanitizedData = chartConfig.data.map(trace => {
    if (!trace || typeof trace !== 'object') return {};
    
    // Ensure trace has required properties
    const sanitizedTrace = {
      type: trace.type || 'scatter',
      mode: trace.mode || 'markers',
      ...trace
    };

    // Ensure x and y arrays exist and are valid
    if (trace.x && Array.isArray(trace.x)) {
      sanitizedTrace.x = trace.x.filter(val => val != null && !isNaN(Number(val)));
    }
    if (trace.y && Array.isArray(trace.y)) {
      sanitizedTrace.y = trace.y.filter(val => val != null && !isNaN(Number(val)));
    }

    return sanitizedTrace;
  }).filter(trace => trace.x && trace.y && trace.x.length > 0 && trace.y.length > 0);

  // Default config if not provided
  const defaultConfig = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    toImageButtonOptions: {
      format: 'png' as const,
      filename: 'custom_chart',
      height: 500,
      width: 800,
      scale: 1
    }
  };

  const config = { ...defaultConfig, ...(chartConfig.config || {}) };

  // Enhance layout with better styling and null safety
  const baseLayout = chartConfig.layout || {};
  const enhancedLayout = {
    ...baseLayout,
    autosize: true,
    showlegend: true,
    margin: {
      l: 60,
      r: 20,
      t: 40,
      b: 60,
      ...(baseLayout.margin || {})
    },
    font: {
      family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      size: 12,
      color: '#374151',
      ...(baseLayout.font || {})
    },
    hoverlabel: {
      bgcolor: 'white',
      bordercolor: '#d1d5db',
      font: { size: 12 },
      ...(baseLayout.hoverlabel || {})
    },
    plot_bgcolor: 'rgba(255,255,255,0.9)',
    paper_bgcolor: 'rgba(255,255,255,1)'
  };

  return (
    <div className={`w-full bg-white rounded-lg shadow-lg p-4 ${className}`}>
      {/* Chart Header */}
      {chartRequestInfo && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-gray-800">
              {chartRequestInfo.title}
            </h3>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-md">
                {chartRequestInfo.chart_type.replace('_', ' ').toUpperCase()}
              </span>
            </div>
          </div>
          
          {chartRequestInfo.explanation && (
            <p className="text-sm text-gray-600 mb-2">
              {chartRequestInfo.explanation}
            </p>
          )}
          
          <div className="flex items-center space-x-4 text-xs text-gray-500">
            <div className="flex items-center space-x-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              <span>X-axis: {chartRequestInfo.x_axis.replace('_', ' ')}</span>
            </div>
            <div className="flex items-center space-x-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Y-axis: {chartRequestInfo.y_axis.replace('_', ' ')}</span>
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="rounded-lg overflow-hidden border border-gray-200 bg-white">
        <div className="w-full h-[500px] flex items-center justify-center">
          <Plot
            data={sanitizedData}
            layout={enhancedLayout}
            config={config}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler={true}
            className="w-full h-full"
            onError={(error) => {
              console.error('Plotly error:', error);
              setError('Failed to render chart');
            }}
            onInitialized={() => setIsLoading(false)}
          />
        </div>
      </div>

      {/* Chart Footer */}
      <div className="mt-3 pt-3 border-t border-gray-100">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center space-x-4">
            <span className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span>{sanitizedData.length} data series</span>
            </span>
            {sanitizedData[0] && (sanitizedData[0] as { x?: unknown[] }).x && (
              <span className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                <span>{((sanitizedData[0] as { x: unknown[] }).x || []).length} data points</span>
              </span>
            )}
          </div>
          <div className="text-gray-400">
            Custom chart generated by AI
          </div>
        </div>
      </div>
    </div>
  );
};

export default CustomChart;