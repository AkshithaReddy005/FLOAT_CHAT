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
    if (!trace || typeof trace !== 'object') return null;

    // Ensure trace has required properties and clean up any undefined/null values
    const sanitizedTrace: Record<string, any> = {
      type: trace.type || 'scatter',
      mode: trace.mode || 'markers'
    };

    // Copy all valid properties from trace, excluding null/undefined values
    Object.keys(trace).forEach(key => {
      const value = (trace as Record<string, any>)[key];
      if (value != null) {
        sanitizedTrace[key] = value;
      }
    });

    // Ensure x and y arrays exist and are valid
    if (trace.x && Array.isArray(trace.x)) {
      sanitizedTrace.x = trace.x.filter(val => val != null && !isNaN(Number(val)));
    }
    if (trace.y && Array.isArray(trace.y)) {
      sanitizedTrace.y = trace.y.filter(val => val != null && !isNaN(Number(val)));
    }

    // Enhance hover information
    if (sanitizedTrace.x && sanitizedTrace.y) {
      const xLabel = chartRequestInfo?.x_axis || 'X';
      const yLabel = chartRequestInfo?.y_axis || 'Y';

      // Create custom hover template for better tooltips
      sanitizedTrace.hovertemplate =
        `<b>%{fullData.name}</b><br>` +
        `${xLabel.replace('_', ' ')}: %{x}<br>` +
        `${yLabel.replace('_', ' ')}: %{y}<br>` +
        `<extra></extra>`;

      // Add custom hover info if not already present
      if (!sanitizedTrace.hoverinfo) {
        sanitizedTrace.hoverinfo = 'x+y+name';
      }

      // Enhance marker styling for better visibility
      if (sanitizedTrace.type === 'scatter' || !sanitizedTrace.type) {
        sanitizedTrace.marker = {
          size: 8,
          opacity: 0.8,
          line: {
            width: 1,
            color: 'rgba(255,255,255,0.8)'
          },
          ...(sanitizedTrace.marker || {})
        };
      }
    }

    // Only return trace if it has valid x and y data
    if (sanitizedTrace.x && sanitizedTrace.y &&
        sanitizedTrace.x.length > 0 && sanitizedTrace.y.length > 0) {
      return sanitizedTrace;
    }
    return null;
  }).filter(trace => trace !== null);

  // Ensure we have valid sanitized data before rendering
  if (!sanitizedData || sanitizedData.length === 0) {
    return (
      <div className={`w-full bg-white rounded-lg shadow-lg p-6 ${className}`}>
        <div className="text-center text-gray-500">
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Invalid Chart Data</h3>
          <p className="text-sm text-gray-600">The chart data contains invalid values and cannot be rendered.</p>
        </div>
      </div>
    );
  }

  // Default config if not provided
  const defaultConfig = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d'],
    modeBarButtonsToAdd: ['hoverclosest', 'hovercompare'],
    toImageButtonOptions: {
      format: 'png' as const,
      filename: 'custom_chart',
      height: 500,
      width: 800,
      scale: 2
    },
    scrollZoom: true,
    doubleClick: 'reset+autosize' as const
  };

  const config = { ...defaultConfig, ...(chartConfig.config || {}) };

  // Enhance layout with better styling and null safety
  const baseLayout = chartConfig.layout || {};

  // Sanitize layout to remove null/undefined values
  const cleanLayout = Object.keys(baseLayout).reduce((acc, key) => {
    const value = (baseLayout as Record<string, any>)[key];
    if (value != null) {
      acc[key] = value;
    }
    return acc;
  }, {} as Record<string, any>);

  const enhancedLayout = {
    ...cleanLayout,
    autosize: true,
    showlegend: true,
    margin: {
      l: 60,
      r: 20,
      t: 40,
      b: 60,
      ...(cleanLayout.margin || {})
    },
    font: {
      family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      size: 12,
      color: '#374151',
      ...(cleanLayout.font || {})
    },
    hoverlabel: {
      bgcolor: 'rgba(255,255,255,0.95)',
      bordercolor: '#e5e7eb',
      borderwidth: 1,
      font: {
        size: 13,
        family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        color: '#374151'
      },
      align: 'left',
      ...(cleanLayout.hoverlabel || {})
    },
    hovermode: 'closest',
    plot_bgcolor: 'rgba(255,255,255,0.9)',
    paper_bgcolor: 'rgba(255,255,255,1)',
    // Enhanced grid and axis styling
    xaxis: {
      gridcolor: 'rgba(229,231,235,0.8)',
      gridwidth: 1,
      zerolinecolor: 'rgba(156,163,175,0.8)',
      zerolinewidth: 1,
      tickfont: {
        size: 11,
        color: '#6B7280'
      },
      title: {
        font: {
          size: 12,
          color: '#374151',
          family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        }
      },
      ...(cleanLayout.xaxis || {})
    },
    yaxis: {
      gridcolor: 'rgba(229,231,235,0.8)',
      gridwidth: 1,
      zerolinecolor: 'rgba(156,163,175,0.8)',
      zerolinewidth: 1,
      tickfont: {
        size: 11,
        color: '#6B7280'
      },
      title: {
        font: {
          size: 12,
          color: '#374151',
          family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        }
      },
      ...(cleanLayout.yaxis || {})
    }
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
          {error ? (
            <div className="text-center text-red-500 p-8">
              <svg className="w-12 h-12 mx-auto mb-4 text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm">{error}</p>
            </div>
          ) : (
            <Plot
              data={sanitizedData}
              layout={enhancedLayout}
              config={config}
              style={{ width: '100%', height: '100%' }}
              useResizeHandler={true}
              className="w-full h-full"
              onError={(error) => {
                console.error('Plotly error:', error);
                setError('Failed to render chart - data may contain invalid values');
              }}
              onInitialized={() => setIsLoading(false)}
            />
          )}
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