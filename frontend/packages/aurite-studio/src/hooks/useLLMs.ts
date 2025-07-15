import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import llmsService from '../services/llms.service';
import { LLMConfig } from '../types';

// Query keys
const QUERY_KEYS = {
  llms: ['llms'],
  llmConfigs: ['llm-configs'],
  llmById: (id: string) => ['llm', id],
  llmConfig: (filename: string) => ['llm-config', filename],
};

// Hook to list all registered LLMs
export const useLLMs = () => {
  return useQuery({
    queryKey: QUERY_KEYS.llms,
    queryFn: () => llmsService.listLLMs(),
    staleTime: 5 * 60 * 1000,
  });
};

// Hook to list LLM configuration files
export const useLLMConfigs = () => {
  return useQuery({
    queryKey: QUERY_KEYS.llmConfigs,
    queryFn: () => llmsService.listLLMConfigs(),
    staleTime: 5 * 60 * 1000,
  });
};

// Hook to get LLM by ID
export const useLLM = (id: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.llmById(id),
    queryFn: () => llmsService.getLLMById(id),
    enabled: enabled && !!id,
  });
};

// Hook to get LLM config by filename
export const useLLMConfig = (filename: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.llmConfig(filename),
    queryFn: () => llmsService.getLLMConfig(filename),
    enabled: enabled && !!filename,
  });
};

// Hook to create and register LLM
export const useCreateLLM = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (config: LLMConfig) => 
      llmsService.createAndRegisterLLM(config),
    onSuccess: (data, variables) => {
      toast.success(`LLM Config "${variables.llm_id}" created successfully`);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llms });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmConfigs });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create LLM configuration');
    },
  });
};

// Hook to update LLM configuration
export const useUpdateLLM = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ filename, config }: { filename: string; config: LLMConfig }) =>
      llmsService.updateLLMConfig(filename, config),
    onSuccess: (data, variables) => {
      toast.success(`LLM Config "${variables.config.llm_id}" updated successfully`);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmConfig(variables.filename) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmById(variables.config.llm_id) });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update LLM configuration');
    },
  });
};

// Hook to delete LLM
export const useDeleteLLM = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (filename: string) => llmsService.deleteLLMConfig(filename),
    onSuccess: (_, filename) => {
      toast.success('LLM configuration deleted successfully');
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llms });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmConfigs });
      queryClient.removeQueries({ queryKey: QUERY_KEYS.llmConfig(filename) });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete LLM configuration');
    },
  });
};

// Hook to get LLMs with their configurations
export const useLLMsWithConfigs = () => {
  const { data: llms = [], isLoading: llmsLoading } = useLLMs();
  const { data: configs = [], isLoading: configsLoading } = useLLMConfigs();

  const llmsWithConfigs = llms.map(llmId => {
    const configFile = configs.find(file => 
      typeof file === 'string' && 
      file.toLowerCase().includes(llmId.toLowerCase().replace(/[^a-z0-9]/g, '_'))
    );
    
    return {
      id: llmId,
      configFile,
      status: 'active' as const,
    };
  });

  return {
    data: llmsWithConfigs,
    isLoading: llmsLoading || configsLoading,
  };
};

// Hook to validate LLM configuration
export const useValidateLLMConfig = () => {
  return (config: Partial<LLMConfig>) => {
    return llmsService.validateConfig(config);
  };
};

// Hook to get LLM presets
export const useLLMPresets = () => {
  return llmsService.getCommonPresets();
};
