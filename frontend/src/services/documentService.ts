import api from './api';
import type { Document, BaseResponse } from '../types';

export const documentService = {
  async list(): Promise<Document[]> {
    const response = await api.get<Document[]>('/documents');
    return response.data;
  },

  async upload(
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<Document>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
    return response.data;
  },

  async process(documentId: string): Promise<BaseResponse> {
    const response = await api.post<BaseResponse>('/documents/process', {
      document_id: documentId,
    });
    return response.data;
  },

  async delete(documentId: string): Promise<BaseResponse> {
    const response = await api.delete<BaseResponse>(`/documents/${documentId}`);
    return response.data;
  },

  async rename(documentId: string, newName: string): Promise<BaseResponse & { name: string }> {
    const response = await api.put<BaseResponse & { name: string }>(`/documents/${documentId}/rename`, {
      name: newName,
    });
    return response.data;
  },

  async getOutput(documentId: string): Promise<{
    document: Document;
    chunk_count: number;
    chunks: Array<{
      id: string;
      document_id: string;
      page_number: number;
      chunk_number: number;
      content: string;
      filename: string;
    }>;
  }> {
    const response = await api.get(`/documents/${documentId}/output`);
    return response.data;
  }
};
