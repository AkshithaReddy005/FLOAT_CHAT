import { ResultCard } from './ResultCard';
import type { ArgoMeasurement } from '../../types';

interface ResultsGridProps {
  results: ArgoMeasurement[];
  query?: string;
}

export const ResultsGrid = ({ results, query }: ResultsGridProps) => {
  if (results.length === 0) {
    return null;
  }

  // Helpers for download
  const triggerDownload = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const buildCsvFromResults = (rows: ArgoMeasurement[]): string => {
    const headers = ['float_id','latitude','longitude','date','depth','temperature','salinity','pressure'];
    const lines = [headers.join(',')];
    for (const r of rows) {
      const vals = [
        // Ensure undefined/null handled gracefully
        (r as any).float_id ?? '',
        (r as any).latitude ?? '',
        (r as any).longitude ?? '',
        (r as any).date ?? '',
        (r as any).depth ?? '',
        (r as any).temperature ?? '',
        (r as any).salinity ?? '',
        (r as any).pressure ?? ''
      ].map(v => typeof v === 'string' && v.includes(',') ? `"${v.replace(/"/g, '""')}"` : v);
      lines.push(vals.join(','));
    }
    return lines.join('\n');
  };

  // Download CSV data for current query with robust fallbacks
  const downloadQueryData = async (queryText: string) => {
    const ts = new Date().toISOString().slice(0,19).replace(/:/g, '-');
    const filename = `argo_data_${ts}.csv`;

    // If no query available, fall back to current results
    if (!queryText || !queryText.trim()) {
      const csv = buildCsvFromResults(results);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      triggerDownload(blob, filename);
      return;
    }

    // Try preferred endpoint first, then fallback
    const payload = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: queryText }) } as RequestInit;
    try {
      let response = await fetch('/api/export/query-csv', payload);
      if (response.status === 404) {
        // Try without /api prefix (depending on dev proxy setup)
        response = await fetch('/export/query-csv', payload);
      }

      if (response.ok) {
        const blob = await response.blob();
        triggerDownload(blob, filename);
        return;
      }

      // Server responded but not OK — fall back to client CSV
      console.warn('Server CSV export failed, falling back to client CSV:', response.statusText);
      const csv = buildCsvFromResults(results);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      triggerDownload(blob, filename);
    } catch (error) {
      console.error('CSV export error, falling back to client CSV:', error);
      const csv = buildCsvFromResults(results);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      triggerDownload(blob, filename);
    }
  };


  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg sm:text-xl font-semibold text-gray-900">
          Search Results
        </h3>
        <div className="flex items-center space-x-3">
          <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
            {results.length} result{results.length !== 1 ? 's' : ''}
          </span>
          
          {/* Download Buttons */}
          <button
            onClick={() => downloadQueryData(query || '')}
            className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download CSV
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-6">
        {results.map((result, index) => (
          <ResultCard key={index} result={result} />
        ))}
      </div>
    </div>
  );
};