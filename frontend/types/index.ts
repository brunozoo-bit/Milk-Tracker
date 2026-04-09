export interface User {
  id: string;
  email: string;
  role: 'admin' | 'factory' | 'producer' | 'collector';
  name: string;
  nickname?: string;
  photo?: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Producer {
  id: string;
  name: string;
  nickname: string;
  email?: string;
  phone?: string;
  photo?: string;
  address?: string;
  created_by: string;
  created_at: string;
}

export interface Collector {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  photo?: string;
  assigned_by: string;
  created_at: string;
}

export interface Collection {
  id: string;
  producer_id: string;
  producer_name: string;
  collector_id: string;
  collector_name: string;
  date: string;
  time: string;
  quantity: number;
  day_of_week: string;
  photo?: string;
  notes?: string;
  synced: boolean;
  created_at: string;
}

export interface OfflineCollection {
  offline_id: string;
  producer_id: string;
  date: string;
  time: string;
  quantity: number;
  day_of_week: string;
  photo?: string;
  notes?: string;
}
