import type { QueryResponse, UploadResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

class ApiService {
  private async makeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        mode: 'cors',
        credentials: 'include',
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error (${response.status}): ${errorText || response.statusText}`);
      }
      
      return response.json();
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        throw new Error(`Unable to connect to server. Please ensure the server is running on ${API_BASE_URL}`);
      }
      throw error;
    }
  }

  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    return this.makeRequest<UploadResponse>('/admin/upload', {
      method: 'POST',
      body: formData,
    });
  }

  async queryData(query: string): Promise<QueryResponse> {
    return this.makeRequest<QueryResponse>('/researcher/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });
  }
}

export const apiService = new ApiService();