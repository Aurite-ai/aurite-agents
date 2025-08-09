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
export const useAgents = () =>
  useQuery({
    queryKey: QUERY_KEYS.agents,
    queryFn: () => agentsService.listAgents(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

// Hook to list agent configuration files
export const useAgentConfigs = () =>
  useQuery({
    queryKey: QUERY_KEYS.agentConfigs,
    queryFn: () => agentsService.listAgentConfigs(),
    staleTime: 5 * 60 * 1000,
  });

// Hook to get agent by ID
export const useAgent = (id: string, enabled = true) =>
  useQuery({
    queryKey: QUERY_KEYS.agentById(id),
    queryFn: () => agentsService.getAgentById(id),
    enabled: enabled && !!id,
  });

// Hook to get agent config by filename
export const useAgentConfig = (filename: string, enabled = true) =>
  useQuery({
    queryKey: QUERY_KEYS.agentConfig(filename),
    queryFn: () => agentsService.getAgentConfig(filename),
    enabled: enabled && !!filename,
  });

// Hook to create and register agent
export const useCreateAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (config: AgentConfig) => agentsService.createAndRegisterAgent(config),
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

// Hook to execute agent (non-streaming)
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

// Hook to execute agent with streaming
export const useExecuteAgentStream = () => {
  const [executingAgents, setExecutingAgents] = useState<Set<string>>(new Set());

  const executeStream = async (
    agentName: string,
    request: ExecuteAgentRequest,
    onStreamEvent: (event: any) => void,
    onComplete: (result: any) => void,
    onError: (error: string) => void
  ) => {
    // Mark agent as executing
    setExecutingAgents(prev => new Set(prev).add(agentName));

    try {
      await agentsService.executeAgentStream(
        agentName,
        request,
        onStreamEvent,
        result => {
          // Mark agent as no longer executing
          setExecutingAgents(prev => {
            const newSet = new Set(prev);
            newSet.delete(agentName);
            return newSet;
          });

          if (result.error) {
            toast.error(`Execution failed: ${result.error}`);
          } else {
            toast.success('Agent executed successfully');
          }

          onComplete(result);
        },
        error => {
          // Mark agent as no longer executing
          setExecutingAgents(prev => {
            const newSet = new Set(prev);
            newSet.delete(agentName);
            return newSet;
          });

          toast.error(`Execution failed: ${error}`);
          onError(error);
        }
      );
    } catch (error) {
      // Mark agent as no longer executing
      setExecutingAgents(prev => {
        const newSet = new Set(prev);
        newSet.delete(agentName);
        return newSet;
      });

      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast.error(`Failed to start streaming: ${errorMessage}`);
      onError(errorMessage);
    }
  };

  const isAgentExecuting = (agentName: string) => executingAgents.has(agentName);

  return {
    executeStream,
    isAgentExecuting,
    isExecuting: executingAgents.size > 0,
  };
};

// Hook to get agents with their configurations
export const useAgentsWithConfigs = () => {
  const { data: agents = [], isLoading: agentsLoading } = useAgents();
  const { data: configs = [], isLoading: configsLoading } = useAgentConfigs();

  const agentsWithConfigs = agents.map(agentName => {
    const configFile = configs.find(
      file =>
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
