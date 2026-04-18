import AsyncStorage from '@react-native-async-storage/async-storage';
import { collectionAPI } from './api';

const QUEUE_KEY = 'offline_collections_queue';

export interface QueuedCollection {
  id: string; // local id
  producer_id: string;
  date: string;
  time: string;
  quantity: number;
  day_of_week: string;
  photo?: string;
  notes?: string;
  created_at: string;
}

export const offlineQueue = {
  async getQueue(): Promise<QueuedCollection[]> {
    try {
      const raw = await AsyncStorage.getItem(QUEUE_KEY);
      return raw ? (JSON.parse(raw) as QueuedCollection[]) : [];
    } catch (err) {
      console.error('Error reading offline queue:', err);
      return [];
    }
  },

  async count(): Promise<number> {
    const queue = await offlineQueue.getQueue();
    return queue.length;
  },

  async addToQueue(item: Omit<QueuedCollection, 'id' | 'created_at'>): Promise<QueuedCollection> {
    const queue = await offlineQueue.getQueue();
    const newItem: QueuedCollection = {
      ...item,
      id: `local_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      created_at: new Date().toISOString(),
    };
    queue.push(newItem);
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
    return newItem;
  },

  async removeFromQueue(id: string): Promise<void> {
    const queue = await offlineQueue.getQueue();
    const next = queue.filter((q) => q.id !== id);
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(next));
  },

  async clear(): Promise<void> {
    await AsyncStorage.removeItem(QUEUE_KEY);
  },

  /**
   * Tries to sync all queued items one by one using collectionAPI.create.
   * Returns { success, failed } counts.
   */
  async sync(): Promise<{ success: number; failed: number; total: number }> {
    const queue = await offlineQueue.getQueue();
    let success = 0;
    let failed = 0;
    const remaining: QueuedCollection[] = [];

    for (const item of queue) {
      try {
        const { id, created_at, ...payload } = item;
        await collectionAPI.create(payload);
        success += 1;
      } catch (err) {
        console.error('Failed to sync item:', item.id, err);
        failed += 1;
        remaining.push(item);
      }
    }

    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(remaining));
    return { success, failed, total: queue.length };
  },
};
