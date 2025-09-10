import type { QueryResponse, UploadResponse, ChatRequest, ChatResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

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

  async chatWithData(message: string): Promise<ChatResponse> {
    return this.makeRequest<ChatResponse>('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });
  }

  async reinitializeConnections(): Promise<any> {
    return this.makeRequest<any>('/admin/reinitialize', {
      method: 'POST',
    });
  }

  async clearChromaDB(): Promise<any> {
    return this.makeRequest<any>('/admin/chroma/clear', {
      method: 'DELETE',
    });
  }

  async clearPostgreSQL(): Promise<any> {
    return this.makeRequest<any>('/admin/postgres/clear', {
      method: 'DELETE',
    });
  }

  async clearAllDatabases(): Promise<any> {
    return this.makeRequest<any>('/admin/databases/clear', {
      method: 'DELETE',
    });
  }

  async getStats(): Promise<any> {
    return this.makeRequest<any>('/admin/stats', {
      method: 'GET',
    });
  }
}

export const apiService = new ApiService();