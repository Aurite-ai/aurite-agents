import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import clientsService from '../services/clients.service';
import { ClientConfig } from '../types';

// Query keys
const QUERY_KEYS = {
  clients: ['clients'],
  activeClients: ['active-clients'],
  clientConfigs: ['client-configs'],
  clientById: (id: string) => ['client', id],
  clientConfig: (filename: string) => ['client-config', filename],
  clientStatus: (name: string) => ['client-status', name],
};

// Hook to list all registered clients
export const useClients = () => {
  return useQuery({
    queryKey: QUERY_KEYS.clients,
    queryFn: () => clientsService.listClients(),
    staleTime: 5 * 60 * 1000,
  });
};

// Hook to list active clients
export const useActiveClients = () => {
  return useQuery({
    queryKey: QUERY_KEYS.activeClients,
    queryFn: () => clientsService.listActiveClients(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
};

// Hook to list client configuration files
export const useClientConfigs = () => {
  return useQuery({
    queryKey: QUERY_KEYS.clientConfigs,
    queryFn: () => clientsService.listClientConfigs(),
    staleTime: 5 * 60 * 1000,
  });
};

// Hook to get client by ID
export const useClient = (id: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.clientById(id),
    queryFn: () => clientsService.getClientById(id),
    enabled: enabled && !!id,
  });
};

// Hook to get client config by filename
export const useClientConfig = (filename: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.clientConfig(filename),
    queryFn: () => clientsService.getClientConfig(filename),
    enabled: enabled && !!filename,
  });
};

// Hook to get client status
export const useClientStatus = (clientName: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.clientStatus(clientName),
    queryFn: () => clientsService.getClientStatus(clientName),
    enabled: enabled && !!clientName,
    refetchInterval: 30000, // Refresh every 30 seconds
  });
};

// Hook to create and register client
export const useCreateClient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (config: ClientConfig) => 
      clientsService.createAndRegisterClient(config),
    onSuccess: (data, variables) => {
      toast.success(`MCP Client "${variables.name}" created successfully`);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clients });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clientConfigs });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.activeClients });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create MCP client');
    },
  });
};

// Hook to update client configuration
export const useUpdateClient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ filename, config }: { filename: string; config: ClientConfig }) =>
      clientsService.updateClientConfig(filename, config),
    onSuccess: (data, variables) => {
      toast.success(`MCP Client "${variables.config.name}" updated successfully`);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clientConfig(variables.filename) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clientById(variables.config.name) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clientStatus(variables.config.name) });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update MCP client');
    },
  });
};

// Hook to delete client
export const useDeleteClient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (filename: string) => clientsService.deleteClientConfig(filename),
    onSuccess: (_, filename) => {
      toast.success('MCP Client deleted successfully');
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clients });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clientConfigs });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.activeClients });
      queryClient.removeQueries({ queryKey: QUERY_KEYS.clientConfig(filename) });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete MCP client');
    },
  });
};

// Hook to get clients with their status
export const useClientsWithStatus = () => {
  const { data: clients = [], isLoading: clientsLoading } = useClients();
  const { data: activeClients = [], isLoading: activeLoading } = useActiveClients();
  const { data: configs = [], isLoading: configsLoading } = useClientConfigs();

  const clientsWithStatus = clients.map(clientName => {
    const isActive = activeClients.includes(clientName);
    const configFile = configs.find(file => 
      typeof file === 'string' && 
      file.toLowerCase().includes(clientName.toLowerCase().replace(/[^a-z0-9]/g, '_'))
    );
    
    return {
      name: clientName,
      configFile,
      status: isActive ? 'connected' : 'disconnected',
      isActive,
    };
  });

  return {
    data: clientsWithStatus,
    isLoading: clientsLoading || activeLoading || configsLoading,
  };
};
