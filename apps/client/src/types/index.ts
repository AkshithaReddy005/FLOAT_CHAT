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

export interface ChartRecommendation {
  type: string;
  chart_type: string;
  reason: string;
}

export interface PipelineFlow {
  total_duration: string;
  steps: Array<{
    step: string;
    duration: string;
    status: string;
    details: string;
  }>;
  parameter_extraction?: {
    duration: string;
    input_query: string;
    extracted_location: string;
    extracted_parameters: string[];
    extracted_years: number[];
    confidence_score: number;
    complexity_level: string;
    is_chart_request: boolean;
    summary: string;
  };
  sql_generation?: {
    generation_duration: string;
    execution_duration: string;
    total_duration: string;
    generated_query: string;
    sql_filters: Record<string, any>;
    records_returned: number;
    sample_results: Record<string, any>[];
  };
  chroma_search?: {
    duration: string;
    search_filters: Record<string, any>;
    documents_found: number;
    n_results_requested: number;
    sample_documents: string[];
    distances: number[];
  };
  api_response?: {
    duration: string;
    response_type: string;
    data_points: number;
    context_documents_used: number;
    visualization_requested: boolean;
    ai_summary: string;
  };
  consistency_validation?: {
    duration: string;
    is_consistent: boolean;
    violations_count: number;
    violations: string[];
    consistency_score: number;
    detailed_report: {
      parameter_drift: Record<string, any>;
      data_quality_issues: Record<string, any>;
      service_inconsistencies: Record<string, any>;
    };
  };
}

export interface ChatResponse {
  response: string;
  data: ArgoMeasurement[];
  pipeline_flow?: PipelineFlow;
  visualization: {
    reasoning?: string;
    chart_recommendations?: ChartRecommendation[];
    available_visualizations?: string[];
    map?: {
      type: string;
      recommended_type?: string;
      reason?: string;
      total_points?: number;
      bounds?: {
        north: number;
        south: number;
        east: number;
        west: number;
        center: {
          lat: number;
          lon: number;
        };
      };
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
      depth_range?: {
        min: number;
        max: number;
      };
      data: Array<{
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
      }>;
    };
    time_series?: {
      type: string;
      data: Array<{
        date: string;
        measurements_count: number;
        temperature_avg: number | null;
        salinity_avg: number | null;
        floats: string[];
      }>;
      date_range?: {
        start: string | null;
        end: string | null;
      };
    };
    statistics?: {
      type: string;
      parameters: {
        temperature?: {
          count: number;
          min: number;
          max: number;
          mean: number;
          median: number;
          std_dev?: number;
          variance?: number;
        };
        salinity?: {
          count: number;
          min: number;
          max: number;
          mean: number;
          median: number;
          std_dev?: number;
          variance?: number;
        };
        depth?: {
          count: number;
          min: number;
          max: number;
          mean: number;
          median: number;
          std_dev?: number;
          variance?: number;
        };
      };
      correlations?: {
        temp_depth?: number;
        sal_depth?: number;
      };
    };
    summary?: {
      total_measurements: number;
      unique_floats: number;
      temperature?: {
        count: number;
        min: number;
        max: number;
        mean: number;
        median: number;
      };
      salinity?: {
        count: number;
        min: number;
        max: number;
        mean: number;
        median: number;
      };
      depth?: {
        count: number;
        min: number;
        max: number;
        mean: number;
        median: number;
      };
      date_range?: {
        start: string;
        end: string;
        span_days: number;
      };
    };
    custom_chart?: {
      type: string;
      config: Record<string, unknown>;
      data: Record<string, unknown>[];
      title?: string;
      description?: string;
    };
    chart_request_info?: {
      requested_chart_type?: string;
      explanation?: string;
      reason?: string;
    };
    type?: string;
    message?: string;
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
  response_summary?: string;
  conversation_summary?: string;
}

export type UserType = 'admin' | 'researcher' | null;