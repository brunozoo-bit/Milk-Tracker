import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Alert,
} from 'react-native';
import { useRouter, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';

export default function ProfileScreen() {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    console.log('Botão sair clicado!');
    
    Alert.alert(
      'Sair',
      'Deseja realmente sair do aplicativo?',
      [
        { 
          text: 'Cancelar', 
          style: 'cancel',
          onPress: () => console.log('Logout cancelado')
        },
        {
          text: 'Sair',
          style: 'destructive',
          onPress: () => {
            console.log('Usuário confirmou logout');
            performLogout();
          },
        },
      ]
    );
  };

  const performLogout = async () => {
    console.log('Executando logout...');
    
    // Limpar estado imediatamente
    await logout();
    
    console.log('Estado limpo, redirecionando...');
    
    // Usar setTimeout para garantir que o estado foi limpo
    setTimeout(() => {
      router.push('/');
    }, 100);
  };

  const getRoleLabel = (role: string) => {
    const roles: any = {
      admin: 'Administrador',
      factory: 'Fábrica',
      producer: 'Produtor',
      collector: 'Coletor',
    };
    return roles[role] || role;
  };

  const getRoleColor = (role: string) => {
    const colors: any = {
      admin: '#f44336',
      factory: '#2196F3',
      producer: '#4CAF50',
      collector: '#FF9800',
    };
    return colors[role] || '#999';
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        {user?.photo ? (
          <Image source={{ uri: user.photo }} style={styles.avatar} />
        ) : (
          <View style={[styles.avatar, styles.avatarPlaceholder]}>
            <Ionicons name="person" size={48} color="#999" />
          </View>
        )}
        
        <Text style={styles.name}>{user?.name}</Text>
        {user?.nickname && <Text style={styles.nickname}>@{user.nickname}</Text>}
        
        <View style={[styles.roleBadge, { backgroundColor: getRoleColor(user?.role || '') }]}>
          <Text style={styles.roleText}>{getRoleLabel(user?.role || '')}</Text>
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.infoCard}>
          <Ionicons name="mail" size={20} color="#666" />
          <View style={styles.infoContent}>
            <Text style={styles.infoLabel}>Email</Text>
            <Text style={styles.infoValue}>{user?.email}</Text>
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Ações</Text>
        
        <TouchableOpacity style={styles.actionButton} onPress={handleLogout}>
          <Ionicons name="log-out" size={24} color="#f44336" />
          <Text style={[styles.actionButtonText, { color: '#f44336' }]}>Sair</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>Controle de Leite v1.0</Text>
        <Text style={styles.footerText}>Sistema de Gestão de Coleta</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#fff',
    alignItems: 'center',
    paddingVertical: 32,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    marginBottom: 16,
  },
  avatarPlaceholder: {
    backgroundColor: '#f0f0f0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  name: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  nickname: {
    fontSize: 16,
    color: '#666',
    marginTop: 4,
  },
  roleBadge: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 16,
    marginTop: 12,
  },
  roleText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  section: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  infoCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    gap: 16,
  },
  infoContent: {
    flex: 1,
  },
  infoLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  infoValue: {
    fontSize: 16,
    color: '#333',
    fontWeight: '500',
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    gap: 16,
    marginBottom: 8,
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    alignItems: 'center',
    padding: 32,
  },
  footerText: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
});
