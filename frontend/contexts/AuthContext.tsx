import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { User, AuthResponse } from '../types';
import { authAPI } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadStoredAuth();
  }, []);

  const loadStoredAuth = async () => {
    try {
      const storedToken = await AsyncStorage.getItem('auth_token');
      const storedUser = await AsyncStorage.getItem('user');
      
      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      }
    } catch (error) {
      console.error('Error loading stored auth:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    try {
      console.log('Login attempt:', email);
      const response: AuthResponse = await authAPI.login(email, password);
      console.log('Login successful:', response.user.email, response.user.role);
      
      setToken(response.access_token);
      setUser(response.user);
      
      await AsyncStorage.setItem('auth_token', response.access_token);
      await AsyncStorage.setItem('user', JSON.stringify(response.user));
      console.log('Auth data saved to storage');
    } catch (error: any) {
      console.error('Login error:', error.response?.data || error.message);
      throw error;
    }
  };

  const logout = async () => {
    try {
      console.log('Logging out user:', user?.email);
      await AsyncStorage.removeItem('auth_token');
      await AsyncStorage.removeItem('user');
      await AsyncStorage.clear(); // Clear all storage for good measure
      
      setToken(null);
      setUser(null);
      console.log('Logout complete');
    } catch (error) {
      console.error('Error during logout:', error);
      // Even if there's an error, clear the state
      setToken(null);
      setUser(null);
    }
  };

  const refreshUser = async () => {
    if (!token) return;
    
    try {
      const userData = await authAPI.getMe(token);
      setUser(userData);
      await AsyncStorage.setItem('user', JSON.stringify(userData));
    } catch (error) {
      console.error('Error refreshing user:', error);
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
