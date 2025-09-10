export interface ArgoMeasurement {
  float_id: string;
  latitude: number;
  longitude: number;
  date: string;
  depth: number;
  temperature: number;
  salinity: number;
  pressure: number;
}

export interface QueryResponse {
  results: ArgoMeasurement[];
  message: string;
}

export interface UploadResponse {
  message: string;
  measurements_count: number;
  duplicate_measurements?: number;
  total_in_file?: number;
  existing_measurements?: number;
  original_upload_date?: string;
  vector_stats?: {
    new_measurements: number;
    duplicates_skipped: number;
    total_processed: number;
  };
  status: string;
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  response: string;
  data: ArgoMeasurement[];
  visualization: {
    map?: {
      type: string;
      points: Array<{
        lat: number;
        lon: number;
        float_id: string;
        temperature: number;
        salinity: number;
        depth: number;
        date: string;
      }>;
    };
    depth_profile?: {
      type: string;
      data: Array<{
        depth: number;
        temperature: number;
        salinity: number;
        float_id: string;
      }>;
    };
    time_series?: {
      type: string;
      data: Array<{
        date: string;
        temperature: number;
        salinity: number;
        float_id: string;
      }>;
    };
    summary?: {
      total_measurements: number;
      unique_floats: number;
      date_range?: {
        start: string;
        end: string;
      };
    };
    type?: string;
  };
  query_params: {
    location?: {
      lat_range: [number, number];
      lon_range: [number, number];
    };
    date_range?: [string, string] | null;
    depth_range?: [number, number] | null;
    parameter?: string | null;
    float_id?: string | null;
    limit: number;
  };
  context_count: number;
}

export type UserType = 'admin' | 'researcher' | null;