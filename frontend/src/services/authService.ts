import api from './api';
import type { LoginCredentials, SignupCredentials, ChangePasswordCredentials, AuthResponse, BaseResponse } from '../types';

export const authService = {
  async signup(credentials: SignupCredentials): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/signup', credentials);
    return response.data;
  },

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/login', credentials);
    if (response.data.session) {
      localStorage.setItem('rag_token', response.data.session.access_token);
      localStorage.setItem('rag_user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  logout(): void {
    localStorage.removeItem('rag_token');
    localStorage.removeItem('rag_user');
  },

  async changePassword(credentials: ChangePasswordCredentials): Promise<BaseResponse> {
    const response = await api.post<BaseResponse>('/auth/change-password', credentials);
    return response.data;
  },

  async forgotPassword(email: string): Promise<BaseResponse> {
    const response = await api.post<BaseResponse>('/auth/forgot-password', { email });
    return response.data;
  },

  getCurrentUser() {
    const userStr = localStorage.getItem('rag_user');
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch {
        return null;
      }
    }
    return null;
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('rag_token');
  }
};
