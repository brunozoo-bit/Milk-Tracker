import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { AppState } from 'react-native';
import { User, AuthResponse } from '../types';
import { authAPI } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string, factoryCode: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false); // Sempre começa false - sem sessão persistente

  useEffect(() => {
    // Limpar storage ao iniciar (sempre começa deslogado)
    clearStorage();
    
    // Listener para deslogar quando app for para background/fechar
    const subscription = AppState.addEventListener('change', handleAppStateChange);
    
    return () => {
      subscription.remove();
    };
  }, []);

  const clearStorage = async () => {
    try {
      // Clear only auth-related keys, preserving offline queue and other data
      await AsyncStorage.multiRemove(['auth_token', 'user']);
      console.log('Auth storage limpo - app iniciado sem sessão');
    } catch (error) {
      console.error('Erro ao limpar storage:', error);
    }
  };

  const handleAppStateChange = async (nextAppState: string) => {
    // Quando app vai para background ou é fechado
    if (nextAppState === 'background' || nextAppState === 'inactive') {
      console.log('App indo para background - fazendo logout');
      await logout();
    }
  };

  const login = async (email: string, password: string, factoryCode: string) => {
    try {
      console.log('Login attempt:', email, 'factory:', factoryCode);
      const response: AuthResponse = await authAPI.login(email, password, factoryCode);
      console.log('Login successful:', response.user.email, response.user.role);
      
      setToken(response.access_token);
      setUser(response.user);
      
      // Salvar no AsyncStorage temporariamente para o interceptor usar
      await AsyncStorage.setItem('auth_token', response.access_token);
      await AsyncStorage.setItem('user', JSON.stringify(response.user));
      
      console.log('Usuário logado (sessão temporária)');
    } catch (error: any) {
      console.error('Login error:', error.response?.data || error.message);
      throw error;
    }
  };

  const logout = async () => {
    try {
      console.log('Logging out user:', user?.email);
      
      // Limpa estado imediatamente
      setToken(null);
      setUser(null);
      
      // Limpa apenas dados de auth (preserva fila offline)
      await AsyncStorage.multiRemove(['auth_token', 'user']);
      
      console.log('Logout complete');
    } catch (error) {
      console.error('Error during logout:', error);
      // Mesmo com erro, limpa o estado
      setToken(null);
      setUser(null);
    }
  };

  const refreshUser = async () => {
    if (!token) return;
    
    try {
      const userData = await authAPI.getMe(token);
      setUser(userData);
    } catch (error) {
      console.error('Error refreshing user:', error);
      // Se falhar ao refresh, desloga
      await logout();
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
