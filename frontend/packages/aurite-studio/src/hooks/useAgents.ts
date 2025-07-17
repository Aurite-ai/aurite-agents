import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import toast from 'react-hot-toast';
import agentsService from '../services/agents.service';
import { AgentConfig, ExecuteAgentRequest } from '../types';

// Query keys
const QUERY_KEYS = {
  agents: ['agents'],
  agentConfigs: ['agent-configs'],
  agentById: (id: string) => ['agent', id],
  agentConfig: (filename: string) => ['agent-config', filename],
};

// Hook to list all registered agents
export const useAgents = () => {
  return useQuery({
    queryKey: QUERY_KEYS.agents,
    queryFn: () => agentsService.listAgents(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Hook to list agent configuration files
export const useAgentConfigs = () => {
  return useQuery({
    queryKey: QUERY_KEYS.agentConfigs,
    queryFn: () => agentsService.listAgentConfigs(),
    staleTime: 5 * 60 * 1000,
  });
};

// Hook to get agent by ID
export const useAgent = (id: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.agentById(id),
    queryFn: () => agentsService.getAgentById(id),
    enabled: enabled && !!id,
  });
};

// Hook to get agent config by filename
export const useAgentConfig = (filename: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.agentConfig(filename),
    queryFn: () => agentsService.getAgentConfig(filename),
    enabled: enabled && !!filename,
  });
};

// Hook to create and register agent
export const useCreateAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (config: AgentConfig) => 
      agentsService.createAndRegisterAgent(config),
    onSuccess: (data, variables) => {
      toast.success(`Agent "${variables.name}" created successfully`);
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agents });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agentConfigs });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create agent');
    },
  });
};

// Hook to update agent configuration
export const useUpdateAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ filename, config }: { filename: string; config: AgentConfig }) =>
      agentsService.updateAgentConfig(filename, config),
    onSuccess: (data, variables) => {
      toast.success(`Agent "${variables.config.name}" updated successfully`);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agentConfig(variables.filename) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agentById(variables.config.name) });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update agent');
    },
  });
};

// Hook to delete agent
export const useDeleteAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (filename: string) => agentsService.deleteAgentConfig(filename),
    onSuccess: (_, filename) => {
      toast.success('Agent deleted successfully');
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agents });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agentConfigs });
      queryClient.removeQueries({ queryKey: QUERY_KEYS.agentConfig(filename) });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete agent');
    },
  });
};

// Hook to execute agent
export const useExecuteAgent = () => {
  const [executingAgents, setExecutingAgents] = useState<Set<string>>(new Set());

  const executeMutation = useMutation({
    mutationFn: ({ agentName, request }: { agentName: string; request: ExecuteAgentRequest }) =>
      agentsService.executeAgent(agentName, request),
    onMutate: ({ agentName }) => {
      setExecutingAgents(prev => new Set(prev).add(agentName));
    },
    onSuccess: (data, { agentName }) => {
      if (data.error) {
        toast.error(`Execution failed: ${data.error}`);
      } else {
        toast.success('Agent executed successfully');
      }
    },
    onError: (error: any, { agentName }) => {
      toast.error(error.response?.data?.detail || 'Failed to execute agent');
    },
    onSettled: (data, error, { agentName }) => {
      setExecutingAgents(prev => {
        const newSet = new Set(prev);
        newSet.delete(agentName);
        return newSet;
      });
    },
  });

  const isAgentExecuting = (agentName: string) => executingAgents.has(agentName);

  return {
    ...executeMutation,
    isAgentExecuting,
    // Keep backward compatibility
    isExecuting: executingAgents.size > 0,
  };
};

// Hook to get agents with their configurations
export const useAgentsWithConfigs = () => {
  const { data: agents = [], isLoading: agentsLoading } = useAgents();
  const { data: configs = [], isLoading: configsLoading } = useAgentConfigs();

  const agentsWithConfigs = agents.map(agentName => {
    const configFile = configs.find(file => 
      typeof file === 'string' && 
      file.toLowerCase().includes(agentName.toLowerCase().replace(/[^a-z0-9]/g, '_'))
    );
    
    return {
      name: agentName,
      configFile,
      status: 'active' as const,
    };
  });

  return {
    data: agentsWithConfigs,
    isLoading: agentsLoading || configsLoading,
  };
};
