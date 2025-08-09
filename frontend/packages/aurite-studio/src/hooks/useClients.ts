import React from 'react';
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
export const useClients = () =>
  useQuery({
    queryKey: QUERY_KEYS.clients,
    queryFn: () => clientsService.listClients(),
    staleTime: 0, // Remove stale time to ensure immediate refetch after invalidation
  });

// Hook to list active clients
export const useActiveClients = () =>
  useQuery({
    queryKey: QUERY_KEYS.activeClients,
    queryFn: () => clientsService.listActiveClients(),
    staleTime: 0, // Remove stale time to ensure immediate refetch after invalidation
    refetchInterval: 30000, // Refresh every 30 seconds
  });

// Hook to list client configuration files
export const useClientConfigs = () =>
  useQuery({
    queryKey: QUERY_KEYS.clientConfigs,
    queryFn: () => clientsService.listClientConfigs(),
    staleTime: 0, // Remove stale time to ensure immediate refetch after invalidation
  });

// Hook to get client by ID
export const useClient = (id: string, enabled = true) =>
  useQuery({
    queryKey: QUERY_KEYS.clientById(id),
    queryFn: () => clientsService.getClientById(id),
    enabled: enabled && !!id,
  });

// Hook to get client config by filename (using MCP server method)
export const useClientConfig = (filename: string, enabled = true) =>
  useQuery({
    queryKey: QUERY_KEYS.clientConfig(filename),
    queryFn: () => clientsService.getMCPServer(filename),
    enabled: enabled && !!filename,
  });

// Hook to get client status
export const useClientStatus = (clientName: string, enabled = true) =>
  useQuery({
    queryKey: QUERY_KEYS.clientStatus(clientName),
    queryFn: () => clientsService.getClientStatus(clientName),
    enabled: enabled && !!clientName,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

// Hook to create and register client
export const useCreateClient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (config: ClientConfig) => clientsService.createAndRegisterClient(config),
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

// Hook to update client configuration (using MCP server method)
export const useUpdateClient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ filename, config }: { filename: string; config: any }) =>
      clientsService.updateMCPServerWithValidation(filename, config),
    onSuccess: (data, variables) => {
      toast.success(`MCP Client "${variables.config.name}" updated successfully`);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clientConfig(variables.filename) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clientById(variables.config.name) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clientStatus(variables.config.name) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clients });
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update MCP client');
    },
  });
};

// Hook to create new MCP server configuration
export const useCreateMCPServer = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, config }: { name: string; config: any }) =>
      clientsService.createMCPServerWithValidation(name, config),
    onSuccess: (data, variables) => {
      toast.success(`MCP Server "${variables.name}" created successfully`);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clients });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clientConfigs });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.activeClients });
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create MCP server');
    },
  });
};

// Hook to register MCP server (connect)
export const useRegisterMCPServer = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (serverName: string) => clientsService.registerMCPServer(serverName),
    onSuccess: async (data, serverName) => {
      toast.success(`MCP Server "${serverName}" connected successfully`);

      // Invalidate queries to mark them as stale
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.activeClients });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.clients });
      queryClient.invalidateQueries({ queryKey: ['client-status'] });

      // Then explicitly refetch to force immediate data refresh
      await queryClient.refetchQueries({ queryKey: QUERY_KEYS.activeClients });
      await queryClient.refetchQueries({ queryKey: QUERY_KEYS.clients });
    },
    onError: (error: any, serverName) => {
      console.error(`Failed to register MCP server "${serverName}":`, error);
      toast.error(`Failed to connect "${serverName}": ${error.message || 'Unknown error'}`);
    },
  });
};

// Hook to unregister MCP server (disconnect)
export const useUnregisterMCPServer = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (serverName: string) => clientsService.unregisterMCPServer(serverName),
    onSuccess: async (data, serverName) => {
      toast.success(`MCP Server "${serverName}" disconnected successfully`);
      // Force immediate refetch of active clients to update status
      await queryClient.refetchQueries({ queryKey: QUERY_KEYS.activeClients });
      await queryClient.refetchQueries({ queryKey: QUERY_KEYS.clients });
    },
    onError: (error: any, serverName) => {
      toast.error(`Failed to disconnect "${serverName}": ${error.message || 'Unknown error'}`);
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

// Enhanced hook to get clients with configuration completeness check
export const useClientsWithStatus = () => {
  const clientsQuery = useClients();
  const activeClientsQuery = useActiveClients();
  const configsQuery = useClientConfigs();

  const { data: clients = [], isLoading: clientsLoading } = clientsQuery;
  const { data: activeClients = [], isLoading: activeLoading } = activeClientsQuery;
  const { data: configs = [], isLoading: configsLoading } = configsQuery;

  // Use useMemo to ensure recalculation when dependencies change
  const clientsWithStatus = React.useMemo(
    () =>
      clients.map(client => {
        // Extract client name properly - handle both string and object formats
        const clientName =
          typeof client === 'string' ? client : (client as any)?.name || String(client);
        const clientNameStr = String(clientName); // Ensure it's a string

        const isActive = activeClients.includes(clientNameStr);
        const configFile = configs.find(
          file =>
            typeof file === 'string' &&
            file.toLowerCase().includes(clientNameStr.toLowerCase().replace(/[^a-z0-9]/g, '_'))
        );

        const clientStatus = {
          name: clientNameStr, // Use the string version
          configFile,
          status: isActive ? 'connected' : 'disconnected',
          isActive,
          isConfigComplete: false, // We'll determine this through a separate mechanism
        };

        return clientStatus;
      }),
    [clients, activeClients, configs]
  );

  return {
    data: clientsWithStatus,
    isLoading: clientsLoading || activeLoading || configsLoading,
  };
};

// Hook to check if a specific client configuration is complete
export const useClientConfigComplete = (clientName: string, enabled = true) =>
  useQuery({
    queryKey: [...QUERY_KEYS.clientConfig(clientName), 'complete'],
    queryFn: async () => {
      try {
        const config = await clientsService.getMCPServer(clientName);

        // Check if configuration is complete (has required transport fields)
        const isComplete =
          config &&
          ((config.transport_type === 'stdio' && config.server_path) ||
            (config.transport_type === 'http_stream' && config.http_endpoint) ||
            (config.transport_type === 'local' && config.command) ||
            // Fallback: if no transport_type specified, check for any transport field
            (!config.transport_type &&
              (config.server_path || config.http_endpoint || config.command)));

        return {
          isComplete: !!isComplete,
          config,
        };
      } catch (error) {
        return {
          isComplete: false,
          config: null,
        };
      }
    },
    enabled: enabled && !!clientName,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
