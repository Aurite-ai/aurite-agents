import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import toast from 'react-hot-toast';
import workflowsService from '../services/workflows.service';
import { WorkflowConfig, ExecuteWorkflowRequest, ExecuteCustomWorkflowRequest } from '../types';

// Query keys
const QUERY_KEYS = {
  workflows: ['workflows'],
  customWorkflows: ['custom-workflows'],
  workflowConfigs: ['workflow-configs'],
  workflowById: (id: string) => ['workflow', id],
  workflowConfig: (filename: string) => ['workflow-config', filename],
};

// Hook to list all registered workflows
export const useWorkflows = () => {
  return useQuery({
    queryKey: QUERY_KEYS.workflows,
    queryFn: () => workflowsService.listWorkflows(),
    staleTime: 5 * 60 * 1000,
  });
};

// Hook to list all custom workflows
export const useCustomWorkflows = () => {
  return useQuery({
    queryKey: QUERY_KEYS.customWorkflows,
    queryFn: () => workflowsService.listCustomWorkflows(),
    staleTime: 5 * 60 * 1000,
  });
};

// Hook to list workflow configuration files
export const useWorkflowConfigs = () => {
  return useQuery({
    queryKey: QUERY_KEYS.workflowConfigs,
    queryFn: () => workflowsService.listWorkflowConfigs(),
    staleTime: 5 * 60 * 1000,
  });
};

// Hook to get workflow by ID
export const useWorkflow = (id: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.workflowById(id),
    queryFn: () => workflowsService.getWorkflowById(id),
    enabled: enabled && !!id,
  });
};

// Hook to get workflow config by filename
export const useWorkflowConfig = (filename: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.workflowConfig(filename),
    queryFn: () => workflowsService.getWorkflowConfig(filename),
    enabled: enabled && !!filename,
  });
};

// Hook to get workflow config by name (for editing) - similar to useLLMConfig
export const useWorkflowConfigByName = (workflowName: string, enabled = true) => {
  return useQuery({
    queryKey: ['workflow-config-by-name', workflowName],
    queryFn: () => workflowsService.getWorkflowConfigByName(workflowName),
    enabled: enabled && !!workflowName,
  });
};

// Hook to create and register workflow
export const useCreateWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (config: WorkflowConfig) => 
      workflowsService.createAndRegisterWorkflow(config),
    onSuccess: (data, variables) => {
      toast.success(`Workflow "${variables.name}" created successfully`);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.workflows });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.workflowConfigs });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create workflow');
    },
  });
};

// Hook to update workflow configuration
export const useUpdateWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ filename, config }: { filename: string; config: WorkflowConfig }) =>
      workflowsService.updateWorkflowConfig(filename, config),
    onSuccess: (data, variables) => {
      toast.success(`Workflow "${variables.config.name}" updated successfully`);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.workflowConfig(variables.filename) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.workflowById(variables.config.name) });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update workflow');
    },
  });
};

// Hook to delete workflow
export const useDeleteWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (filename: string) => workflowsService.deleteWorkflowConfig(filename),
    onSuccess: (_, filename) => {
      toast.success('Workflow deleted successfully');
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.workflows });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.workflowConfigs });
      queryClient.removeQueries({ queryKey: QUERY_KEYS.workflowConfig(filename) });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete workflow');
    },
  });
};

// Hook to execute workflow
export const useExecuteWorkflow = () => {
  const [executingWorkflows, setExecutingWorkflows] = useState<Set<string>>(new Set());

  const executeMutation = useMutation({
    mutationFn: ({ workflowName, request }: { workflowName: string; request: ExecuteWorkflowRequest }) =>
      workflowsService.executeWorkflow(workflowName, request),
    onMutate: ({ workflowName }) => {
      setExecutingWorkflows(prev => new Set(prev).add(workflowName));
    },
    onSuccess: (data, { workflowName }) => {
      if (data.status === 'failed') {
        toast.error(`Workflow failed: ${data.error || 'Unknown error'}`);
      } else {
        toast.success('Workflow executed successfully');
      }
    },
    onError: (error: any, { workflowName }) => {
      toast.error(error.response?.data?.detail || 'Failed to execute workflow');
    },
    onSettled: (data, error, { workflowName }) => {
      setExecutingWorkflows(prev => {
        const newSet = new Set(prev);
        newSet.delete(workflowName);
        return newSet;
      });
    },
  });

  const isWorkflowExecuting = (workflowName: string) => executingWorkflows.has(workflowName);

  return {
    ...executeMutation,
    isWorkflowExecuting,
    // Keep backward compatibility
    isExecuting: executingWorkflows.size > 0,
  };
};

// Hook to execute custom workflow
export const useExecuteCustomWorkflow = () => {
  const [executingWorkflows, setExecutingWorkflows] = useState<Set<string>>(new Set());

  const executeMutation = useMutation({
    mutationFn: ({ workflowName, request }: { workflowName: string; request: ExecuteCustomWorkflowRequest }) =>
      workflowsService.executeCustomWorkflow(workflowName, request),
    onMutate: ({ workflowName }) => {
      setExecutingWorkflows(prev => new Set(prev).add(workflowName));
    },
    onSuccess: (data, { workflowName }) => {
      if (data.status === 'failed') {
        toast.error(`Custom workflow failed: ${data.error || 'Unknown error'}`);
      } else {
        toast.success('Custom workflow executed successfully');
      }
    },
    onError: (error: any, { workflowName }) => {
      toast.error(error.response?.data?.detail || 'Failed to execute custom workflow');
    },
    onSettled: (data, error, { workflowName }) => {
      setExecutingWorkflows(prev => {
        const newSet = new Set(prev);
        newSet.delete(workflowName);
        return newSet;
      });
    },
  });

  const isWorkflowExecuting = (workflowName: string) => executingWorkflows.has(workflowName);

  return {
    ...executeMutation,
    isWorkflowExecuting,
  };
};

// Hook to get workflows with their configurations (following LLM pattern)
export const useWorkflowsWithConfigs = () => {
  const { data: workflows = [], isLoading: workflowsLoading } = useWorkflows();
  const { data: configs = [], isLoading: configsLoading } = useWorkflowConfigs();

  const workflowsWithConfigs = workflows.map(workflowName => {
    const configFile = configs.find(file => 
      typeof file === 'string' && 
      file.toLowerCase().includes(workflowName.toLowerCase().replace(/[^a-z0-9]/g, '_'))
    );
    
    return {
      name: workflowName,
      description: undefined,
      stepCount: 0,
      stepPreview: configFile ? 'Configured and ready' : 'Configuration pending',
      type: 'simple_workflow' as const,
      status: 'active' as const,
      configFile,
    };
  });

  return {
    data: workflowsWithConfigs,
    isLoading: workflowsLoading || configsLoading,
  };
};

// Alias for backward compatibility - now uses the simple pattern
export const useWorkflowsWithFullConfigs = useWorkflowsWithConfigs;

// Hook to get custom workflows with their configurations
export const useCustomWorkflowsWithConfigs = () => {
  const { data: customWorkflows = [], isLoading: customWorkflowsLoading } = useCustomWorkflows();
  const { data: configs = [], isLoading: configsLoading } = useQuery({
    queryKey: QUERY_KEYS.customWorkflows.concat(['configs']),
    queryFn: () => workflowsService.listCustomWorkflowConfigs(),
    staleTime: 5 * 60 * 1000,
  });

  const customWorkflowsWithConfigs = customWorkflows.map(workflowName => {
    const configFile = configs.find(file => 
      typeof file === 'string' && 
      file.toLowerCase().includes(workflowName.toLowerCase().replace(/[^a-z0-9]/g, '_'))
    );
    
    return {
      name: workflowName,
      configFile,
      status: 'active' as const,
      type: 'custom_workflow' as const,
    };
  });

  return {
    data: customWorkflowsWithConfigs,
    isLoading: customWorkflowsLoading || configsLoading,
  };
};

// Hook to get custom workflow config by name (for editing)
export const useCustomWorkflowConfigByName = (workflowName: string, enabled = true) => {
  return useQuery({
    queryKey: ['custom-workflow-config-by-name', workflowName],
    queryFn: () => workflowsService.getCustomWorkflowConfigByName(workflowName),
    enabled: enabled && !!workflowName,
  });
};

// Hook to update custom workflow configuration
export const useUpdateCustomWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ filename, config }: { filename: string; config: any }) =>
      workflowsService.updateCustomWorkflowConfig(filename, config),
    onSuccess: (data, variables) => {
      toast.success(`Custom workflow "${variables.config.name}" updated successfully`);
      queryClient.invalidateQueries({ queryKey: ['custom-workflow-config-by-name', variables.config.name] });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.customWorkflows });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update custom workflow');
    },
  });
};

// Hook to delete custom workflow
export const useDeleteCustomWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (filename: string) => workflowsService.deleteCustomWorkflowConfig(filename),
    onSuccess: (_, filename) => {
      toast.success('Custom workflow deleted successfully');
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.customWorkflows });
      queryClient.invalidateQueries({ queryKey: ['custom-workflow-configs'] });
      queryClient.removeQueries({ queryKey: ['custom-workflow-config', filename] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete custom workflow');
    },
  });
};
