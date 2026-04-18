import React, { useState, useEffect, useCallback, useLayoutEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useRouter, useNavigation, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { collectionAPI } from '../../services/api';
import { offlineQueue } from '../../services/offlineQueue';
import { Collection } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import NetInfo from '@react-native-community/netinfo';

export default function CollectionsScreen() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isOnline, setIsOnline] = useState(true);
  const [pendingCount, setPendingCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);
  const { user } = useAuth();
  const router = useRouter();
  const navigation = useNavigation();

  const canAddCollection = user?.role === 'collector' || user?.role === 'admin' || user?.role === 'factory';
  const canManage = user?.role === 'admin' || user?.role === 'factory';

  useEffect(() => {
    loadCollections();
    loadPendingCount();

    const unsubscribe = NetInfo.addEventListener(state => {
      setIsOnline(state.isConnected ?? false);
    });

    return () => unsubscribe();
  }, []);

  // Refresh pending count whenever screen is focused (e.g. after returning from add-collection)
  useFocusEffect(
    useCallback(() => {
      loadPendingCount();
    }, [])
  );

  const loadPendingCount = async () => {
    const count = await offlineQueue.count();
    setPendingCount(count);
  };

  // Header refresh button (top right)
  useLayoutEffect(() => {
    if (!canManage) {
      navigation.setOptions({ headerRight: undefined });
      return;
    }
    navigation.setOptions({
      headerRight: () => (
        <TouchableOpacity
          onPress={handleHeaderRefresh}
          style={styles.headerButton}
          accessibilityLabel="Atualizar"
        >
          <Ionicons name="refresh" size={24} color="#fff" />
        </TouchableOpacity>
      ),
    });
  }, [navigation, canManage, isRefreshing]);

  const handleHeaderRefresh = async () => {
    setIsRefreshing(true);
    await loadCollections();
    await loadPendingCount();
  };

  const loadCollections = async () => {
    try {
      const data = await collectionAPI.getAll();
      setCollections(data);
    } catch (error) {
      console.error('Error loading collections:', error);
      Alert.alert('Erro', 'Não foi possível carregar as coletas');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setIsRefreshing(true);
    loadCollections();
    loadPendingCount();
  }, []);

  const handleSync = async () => {
    if (pendingCount === 0) {
      Alert.alert('Tudo em dia', 'Não há coletas pendentes para sincronizar.');
      return;
    }
    if (!isOnline) {
      Alert.alert(
        'Sem conexão',
        'Você está offline. Conecte-se à internet para sincronizar as coletas.'
      );
      return;
    }

    setIsSyncing(true);
    try {
      const result = await offlineQueue.sync();
      await loadPendingCount();
      await loadCollections();
      if (result.failed === 0) {
        Alert.alert(
          'Sincronização Concluída',
          `${result.success} coleta(s) enviada(s) com sucesso.`
        );
      } else {
        Alert.alert(
          'Sincronização Parcial',
          `${result.success} enviada(s) · ${result.failed} falha(s). Tente novamente.`
        );
      }
    } catch (err) {
      Alert.alert('Erro', 'Falha ao sincronizar. Tente novamente.');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleDeleteCollection = (id: string, producerName: string) => {
    console.log('Delete button pressed for collection:', id);
    console.log('Current user role:', user?.role);
    Alert.alert(
      'Confirmar Exclusão',
      `Deseja realmente excluir esta coleta de ${producerName}?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Excluir',
          style: 'destructive',
          onPress: async () => {
            try {
              console.log('Attempting to delete collection:', id);
              await collectionAPI.delete(id);
              console.log('Collection deleted successfully');
              loadCollections();
              Alert.alert('Sucesso', 'Coleta excluída com sucesso');
            } catch (error: any) {
              console.error('Error deleting collection:', error);
              Alert.alert('Erro', error.response?.data?.detail || 'Não foi possível excluir a coleta');
            }
          },
        },
      ]
    );
  };

  const renderCollection = ({ item }: { item: Collection }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardHeaderLeft}>
          <Ionicons name="person" size={20} color="#4CAF50" />
          <Text style={styles.producerName}>{item.producer_name}</Text>
        </View>
        <Text style={styles.quantity}>{item.quantity}L</Text>
      </View>
      
      <View style={styles.cardDetails}>
        <View style={styles.detailRow}>
          <Ionicons name="calendar" size={16} color="#666" />
          <Text style={styles.detailText}>{item.date} - {item.day_of_week}</Text>
        </View>
        <View style={styles.detailRow}>
          <Ionicons name="time" size={16} color="#666" />
          <Text style={styles.detailText}>{item.time}</Text>
        </View>
        <View style={styles.detailRow}>
          <Ionicons name="person-outline" size={16} color="#666" />
          <Text style={styles.detailText}>Coletor: {item.collector_name}</Text>
        </View>
      </View>
      
      {!item.synced && (
        <View style={styles.offlineBadge}>
          <Ionicons name="cloud-offline" size={14} color="#FF9800" />
          <Text style={styles.offlineText}>Não sincronizado</Text>
        </View>
      )}
      
      {user?.role === 'admin' && (
        <View style={styles.cardActions}>
          <TouchableOpacity
            style={styles.deleteButton}
            onPress={() => handleDeleteCollection(item.id, item.producer_name)}
          >
            <Ionicons name="trash" size={20} color="#f44336" />
            <Text style={styles.deleteButtonText}>Excluir</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {!isOnline && (
        <View style={styles.offlineBar}>
          <Ionicons name="cloud-offline" size={16} color="#fff" />
          <Text style={styles.offlineBarText}>Modo Offline</Text>
        </View>
      )}

      {canAddCollection && (
        <TouchableOpacity
          style={[
            styles.syncBar,
            pendingCount > 0 ? styles.syncBarPending : styles.syncBarIdle,
          ]}
          onPress={handleSync}
          disabled={isSyncing}
          activeOpacity={0.8}
        >
          {isSyncing ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Ionicons
              name={pendingCount > 0 ? 'cloud-upload' : 'cloud-done'}
              size={18}
              color="#fff"
            />
          )}
          <Text style={styles.syncBarText}>
            {isSyncing
              ? 'Sincronizando...'
              : pendingCount > 0
              ? `Sincronizar ${pendingCount} coleta(s) offline`
              : 'Tudo sincronizado'}
          </Text>
          {pendingCount > 0 && !isSyncing && (
            <View style={styles.syncBadge}>
              <Text style={styles.syncBadgeText}>{pendingCount}</Text>
            </View>
          )}
        </TouchableOpacity>
      )}

      <FlatList
        data={collections}
        renderItem={renderCollection}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={onRefresh}
            colors={['#4CAF50']}
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="water-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Nenhuma coleta registrada</Text>
          </View>
        }
      />
      
      {canAddCollection && (
        <TouchableOpacity
          style={styles.fab}
          onPress={() => router.push('/add-collection')}
        >
          <Ionicons name="add" size={32} color="#fff" />
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  offlineBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FF9800',
    padding: 8,
    gap: 8,
  },
  offlineBarText: {
    color: '#fff',
    fontWeight: '600',
  },
  syncBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    gap: 8,
  },
  syncBarPending: {
    backgroundColor: '#FF5722',
  },
  syncBarIdle: {
    backgroundColor: '#43A047',
  },
  syncBarText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 14,
  },
  syncBadge: {
    backgroundColor: '#fff',
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    paddingHorizontal: 6,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 4,
  },
  syncBadgeText: {
    color: '#FF5722',
    fontWeight: '700',
    fontSize: 12,
  },
  headerButton: {
    marginRight: 12,
    padding: 6,
  },
  listContainer: {
    padding: 16,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  cardHeaderLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  producerName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  quantity: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  cardDetails: {
    gap: 6,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  detailText: {
    fontSize: 14,
    color: '#666',
  },
  offlineBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  offlineText: {
    fontSize: 12,
    color: '#FF9800',
    fontWeight: '600',
  },
  cardActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  deleteButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: '#ffebee',
  },
  deleteButtonText: {
    fontSize: 14,
    color: '#f44336',
    fontWeight: '600',
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    marginTop: 16,
  },
  fab: {
    position: 'absolute',
    right: 24,
    bottom: 24,
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#4CAF50',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
});
