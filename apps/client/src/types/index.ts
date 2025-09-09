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
  status: string;
}

export type UserType = 'admin' | 'researcher' | null;