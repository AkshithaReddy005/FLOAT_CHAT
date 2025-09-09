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

export type UserType = 'admin' | 'researcher' | null;