import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/services/apiClient';

export type ConnectionStatus = 'connected' | 'disconnected' | 'checking';

export interface ApiConnectionState {
  status: ConnectionStatus;
  lastChecked: Date | null;
  error: string | null;
}

export function useApiConnection(pollInterval: number = 30000) {
  const [state, setState] = useState<ApiConnectionState>({
    status: 'checking',
    lastChecked: null,
    error: null,
  });

  const checkConnection = useCallback(async () => {
    setState(prev => ({ ...prev, status: 'checking', error: null }));
    
    try {
      await apiClient.system.getStatus();
      setState({
        status: 'connected',
        lastChecked: new Date(),
        error: null,
      });
    } catch (error) {
      setState({
        status: 'disconnected',
        lastChecked: new Date(),
        error: error instanceof Error ? error.message : 'Connection failed',
      });
    }
  }, []);

  // Initial check
  useEffect(() => {
    checkConnection();
  }, [checkConnection]);

  // Periodic checks
  useEffect(() => {
    const interval = setInterval(checkConnection, pollInterval);
    return () => clearInterval(interval);
  }, [checkConnection, pollInterval]);

  return {
    ...state,
    checkConnection,
  };
}
