import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import llmsService from '../services/llms.service';
import { LLMConfig } from '../types';
import { formatLLMTestError } from '../utils/formatters';

// Define the LLMTestResult type locally to avoid import issues
interface LLMTestResult {
  status: 'success' | 'error';
  llm_config_id: string;
  metadata?: {
    provider: string;
    model: string;
    temperature?: number;
    max_tokens?: number;
  };
  error?: {
    message: string;
    error_type?: string;
  };
}

// LLM data type definition removed as it's not used

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
      toast.success(`LLM Config "${variables.name}" created successfully`);

      // Invalidate all LLM-related queries to ensure UI updates immediately
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llms });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmConfigs });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmById(variables.name) });
      queryClient.invalidateQueries({ queryKey: ['llms-with-full-configs'] });
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
      toast.success(`LLM Config "${variables.config.name}" updated successfully`);

      // Invalidate all LLM-related queries to ensure UI updates immediately
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llms });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmConfigs });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmConfig(variables.filename) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmById(variables.config.name) });
      queryClient.invalidateQueries({ queryKey: ['llms-with-full-configs'] });
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

// Hook to test LLM configuration
export const useTestLLM = (
  onMarkAsFailed?: (_llmConfigId: string) => void,
  onMarkAsSuccess?: (_llmConfigId: string) => void
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (llmConfigId: string) => {
      try {
        const result = await llmsService.testLLMConfig(llmConfigId);
        return result;
      } catch (error) {
        // Error will be handled by onError callback
        throw error;
      }
    },
    onSuccess: (result: LLMTestResult, llmConfigId: string) => {
      if (result.status === 'success') {
        toast.success(`${llmConfigId} tested successfully!`);
        // Mark as successful (clear from failed list)
        onMarkAsSuccess?.(llmConfigId);
      } else {
        toast.error(`Test failed: ${result.error?.message || 'Unknown error'}`);
        // Mark as failed
        onMarkAsFailed?.(llmConfigId);
      }

      // Invalidate queries to refresh validation status
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llms });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmConfigs });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmById(llmConfigId) });
      queryClient.invalidateQueries({ queryKey: ['llms-with-full-configs'] });
    },
    onError: (error: any, llmConfigId: string) => {
      // Mark as failed
      onMarkAsFailed?.(llmConfigId);

      // Use the improved error formatter
      const userFriendlyMessage = formatLLMTestError(llmConfigId, error);

      toast.error(`${userFriendlyMessage}`);
    },
  });
};

// Hook to get LLMs with their configurations
export const useLLMsWithConfigs = () => {
  const { data: llms = [], isLoading: llmsLoading } = useLLMs();
  const { data: configs = [], isLoading: configsLoading } = useLLMConfigs();

  // Process the LLM data - the API returns full config objects, not just IDs
  const configQueries = useQuery({
    queryKey: ['llms-with-full-configs', llms],
    queryFn: async () => {
      const llmsWithConfigs = llms
        .map((llmData: any) => {
          // Handle both string and object formats
          let llmId: string;
          let fullConfig: any;

          if (typeof llmData === 'string') {
            llmId = llmData;
            fullConfig = null;
          } else if (llmData && typeof llmData === 'object' && llmData.name) {
            llmId = llmData.name;
            fullConfig = llmData; // The API already returns the full config
          } else {
            // Invalid LLM data format - skip this entry
            return null;
          }

          // Find matching config file
          const configFile = configs.find(
            file =>
              typeof file === 'string' &&
              file.toLowerCase().includes(llmId.toLowerCase().replace(/[^a-z0-9]/g, '_'))
          );

          return {
            id: llmId,
            configFile,
            status: 'active' as const,
            validated_at: fullConfig?.validated_at || null,
            provider: fullConfig?.provider,
            model: fullConfig?.model,
            fullConfig,
          };
        })
        .filter(Boolean); // Remove any null entries

      return llmsWithConfigs;
    },
    enabled: !llmsLoading && !configsLoading && llms.length > 0,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  return {
    data: configQueries.data || [],
    isLoading: llmsLoading || configsLoading || configQueries.isLoading,
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
