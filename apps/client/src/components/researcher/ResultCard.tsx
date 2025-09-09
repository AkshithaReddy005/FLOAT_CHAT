import type { ArgoMeasurement } from '../../types';

interface ResultCardProps {
  result: ArgoMeasurement;
}

export const ResultCard = ({ result }: ResultCardProps) => {
  return (
    <article 
      className="bg-white border border-gray-200 rounded-lg p-4 sm:p-5 shadow-sm hover:shadow-md transition-shadow duration-200 focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2"
      aria-labelledby={`float-${result.float_id}-title`}
    >
      <div className="space-y-3">
        <div className="flex items-center justify-between border-b border-gray-100 pb-2">
          <h4 id={`float-${result.float_id}-title`} className="font-semibold text-gray-900 text-sm">
            Float #{result.float_id}
          </h4>
          <time className="text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded" dateTime={result.date}>
            {result.date}
          </time>
        </div>
        
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="font-medium text-gray-600">Location</dt>
            <dd className="text-gray-900 font-mono text-xs">
              <span aria-label={`Latitude ${result.latitude} degrees North, Longitude ${result.longitude} degrees East`}>
                {result.latitude}°N, {result.longitude}°E
              </span>
            </dd>
          </div>
          
          <div>
            <dt className="font-medium text-gray-600">Depth</dt>
            <dd className="text-gray-900">
              <span aria-label={`${result.depth} meters deep`}>
                {result.depth}m
              </span>
            </dd>
          </div>
          
          <div>
            <dt className="font-medium text-gray-600">Temperature</dt>
            <dd className="text-gray-900">
              <span aria-label={`${result.temperature} degrees Celsius`}>
                {result.temperature}°C
              </span>
            </dd>
          </div>
          
          <div>
            <dt className="font-medium text-gray-600">Salinity</dt>
            <dd className="text-gray-900" aria-label={`Salinity level ${result.salinity}`}>
              {result.salinity}
            </dd>
          </div>
        </dl>
      </div>
    </article>
  );
};