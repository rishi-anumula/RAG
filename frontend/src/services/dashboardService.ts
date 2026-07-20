import api from './api';
import type { DashboardMetrics } from '../types';

export const dashboardService = {
  async getMetrics(): Promise<DashboardMetrics> {
    const response = await api.get<DashboardMetrics>('/dashboard');
    return response.data;
  }
};
export default dashboardService;
