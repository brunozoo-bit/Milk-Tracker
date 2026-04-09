import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { reportAPI } from '../../services/api';
import { format, subDays, startOfWeek, startOfMonth } from 'date-fns';

export default function ReportsScreen() {
  const [isLoading, setIsLoading] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<'today' | 'week' | 'month'>('today');

  const getPeriodDates = () => {
    const today = new Date();
    let startDate, endDate;

    switch (selectedPeriod) {
      case 'today':
        startDate = format(today, 'yyyy-MM-dd');
        endDate = format(today, 'yyyy-MM-dd');
        break;
      case 'week':
        startDate = format(startOfWeek(today), 'yyyy-MM-dd');
        endDate = format(today, 'yyyy-MM-dd');
        break;
      case 'month':
        startDate = format(startOfMonth(today), 'yyyy-MM-dd');
        endDate = format(today, 'yyyy-MM-dd');
        break;
    }

    return { startDate, endDate };
  };

  const loadSummary = async () => {
    setIsLoading(true);
    try {
      const { startDate, endDate } = getPeriodDates();
      const data = await reportAPI.getSummary(startDate, endDate);
      setSummary(data);
    } catch (error) {
      console.error('Error loading summary:', error);
      Alert.alert('Erro', 'Não foi possível carregar o relatório');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const { startDate, endDate } = getPeriodDates();
      Alert.alert(
        'Exportar Relatório',
        'A exportação CSV estará disponível em breve',
        [{ text: 'OK' }]
      );
    } catch (error) {
      Alert.alert('Erro', 'Não foi possível exportar o relatório');
    }
  };

  React.useEffect(() => {
    loadSummary();
  }, [selectedPeriod]);

  const renderPeriodButton = (period: 'today' | 'week' | 'month', label: string) => (
    <TouchableOpacity
      style={[styles.periodButton, selectedPeriod === period && styles.periodButtonActive]}
      onPress={() => setSelectedPeriod(period)}
    >
      <Text
        style={[styles.periodButtonText, selectedPeriod === period && styles.periodButtonTextActive]}
      >
        {label}
      </Text>
    </TouchableOpacity>
  );

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Relatórios</Text>
        <TouchableOpacity style={styles.exportButton} onPress={handleExport}>
          <Ionicons name="download" size={20} color="#fff" />
          <Text style={styles.exportButtonText}>Exportar CSV</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.periodSelector}>
        {renderPeriodButton('today', 'Hoje')}
        {renderPeriodButton('week', 'Semana')}
        {renderPeriodButton('month', 'Mês')}
      </View>

      {isLoading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#4CAF50" />
        </View>
      ) : summary ? (
        <View>
          <View style={styles.summaryCards}>
            <View style={styles.summaryCard}>
              <Ionicons name="water" size={32} color="#4CAF50" />
              <Text style={styles.summaryValue}>{summary.total_quantity.toFixed(1)}L</Text>
              <Text style={styles.summaryLabel}>Total Coletado</Text>
            </View>

            <View style={styles.summaryCard}>
              <Ionicons name="calendar" size={32} color="#2196F3" />
              <Text style={styles.summaryValue}>{summary.total_collections}</Text>
              <Text style={styles.summaryLabel}>Coletas</Text>
            </View>

            <View style={styles.summaryCard}>
              <Ionicons name="analytics" size={32} color="#FF9800" />
              <Text style={styles.summaryValue}>{summary.average_quantity.toFixed(1)}L</Text>
              <Text style={styles.summaryLabel}>Média</Text>
            </View>
          </View>

          {summary.by_producer && summary.by_producer.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Por Produtor</Text>
              {summary.by_producer.map((producer: any, index: number) => (
                <View key={index} style={styles.producerCard}>
                  <View style={styles.producerInfo}>
                    <Text style={styles.producerName}>{producer.producer_name}</Text>
                    <Text style={styles.producerNickname}>@{producer.producer_nickname}</Text>
                  </View>
                  <View style={styles.producerStats}>
                    <Text style={styles.producerQuantity}>{producer.total_quantity.toFixed(1)}L</Text>
                    <Text style={styles.producerCollections}>{producer.collection_count} coletas</Text>
                  </View>
                </View>
              ))}
            </View>
          )}
        </View>
      ) : (
        <View style={styles.emptyContainer}>
          <Ionicons name="bar-chart-outline" size={64} color="#ccc" />
          <Text style={styles.emptyText}>Nenhum dado disponível</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  exportButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4CAF50',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    gap: 6,
  },
  exportButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  periodSelector: {
    flexDirection: 'row',
    padding: 16,
    gap: 8,
  },
  periodButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#fff',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  periodButtonActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  periodButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  periodButtonTextActive: {
    color: '#fff',
  },
  loadingContainer: {
    padding: 32,
    alignItems: 'center',
  },
  summaryCards: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
  },
  summaryCard: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  summaryValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 8,
  },
  summaryLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
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
  producerCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 8,
  },
  producerInfo: {
    flex: 1,
  },
  producerName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  producerNickname: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  producerStats: {
    alignItems: 'flex-end',
  },
  producerQuantity: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  producerCollections: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
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
});
