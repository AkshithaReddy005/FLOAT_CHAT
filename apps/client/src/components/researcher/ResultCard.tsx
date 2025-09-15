import type { ArgoMeasurement } from '../../types';

interface ResultCardProps {
  result: ArgoMeasurement;
}

export const ResultCard = ({ result }: ResultCardProps) => {
  // Robust date formatter: show YYYY-MM-DD; keep full value in tooltip
  const rawDate = result.date ?? '';
  const displayDate = (() => {
    if (!rawDate) return '';
    // Try standard Date parsing first
    const d = new Date(rawDate);
    if (!isNaN(d.getTime())) {
      // Format as YYYY-MM-DD in UTC to avoid TZ shifting the day
      const y = d.getUTCFullYear();
      const m = String(d.getUTCMonth() + 1).padStart(2, '0');
      const day = String(d.getUTCDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    }
    // Fallbacks: handle ISO-like strings and partial dates
    const ten = rawDate.slice(0, 10);
    if (/^\d{4}-\d{2}-\d{2}$/.test(ten)) return ten;
    const parts = rawDate.split(/[T\s]/)[0];
    if (/^\d{4}-\d{2}-\d{2}$/.test(parts)) return parts;
    return rawDate; // last resort
  })();
  return (
    <article 
      className="bg-white border border-gray-200 rounded-lg p-4 sm:p-5 shadow-sm hover:shadow-md transition-shadow duration-200 focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2"
      aria-labelledby={`float-${result.float_id}-title`}
    >
      <div className="space-y-3">
        <div className="flex items-center justify-between border-b border-gray-100 pb-2 ">
          <h4 id={`float-${result.float_id}-title`} className="font-semibold text-gray-900 text-sm mr-2">
            Float #{result.float_id} 
          </h4>
          <time
            className="text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded"
            dateTime={rawDate}
            title={rawDate}
          >
            {displayDate}
          </time>
        </div>
        
        <dl className="space-y-3 text-sm">
          <div className="grid grid-cols-1 gap-3">
            <div>
              <dt className="font-medium text-gray-600 mb-1">Location</dt>
              <dd className="text-gray-900 font-mono text-xs">
                <span aria-label={`Latitude ${result.latitude} degrees North, Longitude ${result.longitude} degrees East`}>
                  {Number(result.latitude).toFixed(4)}°N, {Number(result.longitude).toFixed(4)}°E
                </span>
              </dd>
            </div>
          </div>
          
          <div className="grid grid-cols-3 gap-3">
            <div>
              <dt className="font-medium text-gray-600 mb-1">Depth</dt>
              <dd className="text-gray-900">
                <span aria-label={`${result.depth} meters deep`}>
                  {Number(result.depth).toFixed(1)}m
                </span>
              </dd>
            </div>
            
            <div>
              <dt className="font-medium text-gray-600 mb-1">Temp</dt>
              <dd className="text-gray-900">
                <span aria-label={`${result.temperature} degrees Celsius`}>
                  {Number(result.temperature).toFixed(2)}°C
                </span>
              </dd>
            </div>
            
            <div>
              <dt className="font-medium text-gray-600 mb-1">Salinity</dt>
              <dd className="text-gray-900" aria-label={`Salinity level ${result.salinity}`}>
                {Number(result.salinity).toFixed(3)}
              </dd>
            </div>
          </div>
        </dl>
      </div>
    </article>
  );
};