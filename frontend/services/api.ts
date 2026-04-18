import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { AuthResponse, User, Producer, Collector, Collection, OfflineCollection } from '../types';

const API_BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('auth_token');
  console.log('Interceptor - Token exists:', !!token);
  console.log('Interceptor - Request URL:', config.url);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    console.log('Interceptor - Authorization header added');
  } else {
    console.warn('Interceptor - No token found in storage!');
  }
  return config;
});

// Auth API
export const authAPI = {
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await api.post('/auth/login', { 
      factory_code: 'principal',
      email, 
      password 
    });
    return response.data;
  },
  
  getMe: async (token: string): Promise<User> => {
    const response = await api.get('/auth/me', {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },
  
  register: async (userData: any): Promise<User> => {
    const response = await api.post('/auth/register', userData);
    return response.data;
  },
};

// Producer API
export const producerAPI = {
  getAll: async (): Promise<Producer[]> => {
    const response = await api.get('/producers');
    return response.data;
  },
  
  getById: async (id: string): Promise<Producer> => {
    const response = await api.get(`/producers/${id}`);
    return response.data;
  },
  
  create: async (data: any): Promise<Producer> => {
    const response = await api.post('/producers', data);
    return response.data;
  },
  
  update: async (id: string, data: any): Promise<Producer> => {
    const response = await api.put(`/producers/${id}`, data);
    return response.data;
  },
  
  delete: async (id: string): Promise<void> => {
    await api.delete(`/producers/${id}`);
  },
};

// Collector API
export const collectorAPI = {
  getAll: async (): Promise<Collector[]> => {
    const response = await api.get('/collectors');
    return response.data;
  },
  
  create: async (data: any): Promise<Collector> => {
    const response = await api.post('/collectors', data);
    return response.data;
  },
  
  delete: async (id: string): Promise<void> => {
    await api.delete(`/collectors/${id}`);
  },
};

// Collection API
export const collectionAPI = {
  getAll: async (params?: { start_date?: string; end_date?: string; producer_id?: string }): Promise<Collection[]> => {
    const response = await api.get('/collections', { params });
    return response.data;
  },
  
  getById: async (id: string): Promise<Collection> => {
    const response = await api.get(`/collections/${id}`);
    return response.data;
  },
  
  create: async (data: any): Promise<Collection> => {
    const response = await api.post('/collections', data);
    return response.data;
  },
  
  update: async (id: string, data: any): Promise<Collection> => {
    const response = await api.put(`/collections/${id}`, data);
    return response.data;
  },
  
  delete: async (id: string): Promise<void> => {
    await api.delete(`/collections/${id}`);
  },
  
  sync: async (collections: OfflineCollection[]): Promise<any> => {
    const response = await api.post('/collections/sync', collections);
    return response.data;
  },
};

// Report API
export const reportAPI = {
  getSummary: async (startDate: string, endDate: string, producerId?: string): Promise<any> => {
    const params: any = { start_date: startDate, end_date: endDate };
    if (producerId) params.producer_id = producerId;
    
    const response = await api.get('/reports/summary', { params });
    return response.data;
  },
  
  exportCSV: async (startDate: string, endDate: string, producerId?: string): Promise<string> => {
    const params: any = { start_date: startDate, end_date: endDate };
    if (producerId) params.producer_id = producerId;

    const response = await api.get('/reports/export', {
      params,
      responseType: 'text',
      transformResponse: [(data) => data], // keep raw text
    });
    return response.data as string;
  },
};

export default api;
