import apiClient from './apiClient';
import { 
  LLMConfig as LocalLLMConfig,
  SuccessResponse
} from '../types';
import {
  ApiError,
  TimeoutError,
  CancellationError,
  LLMConfig as ApiLLMConfig,
} from '@aurite/api-client';

class LLMsService {
  // List all registered LLM configurations
  async listLLMs(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('llm');
    } catch (error) {
      this.handleError(error, 'Failed to list LLMs');
      throw error;
    }
  }

  // List LLM configuration files
  async listLLMConfigs(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('llm');
    } catch (error) {
      this.handleError(error, 'Failed to list LLM configurations');
      throw error;
    }
  }

  // Get LLM configuration by ID
  async getLLMById(id: string): Promise<LocalLLMConfig> {
    try {
      const config = await apiClient.config.getConfig('llm', id);
      return this.mapToLocalLLMConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get LLM configuration for ${id}`);
      throw error;
    }
  }

  // Get LLM configuration by filename
  async getLLMConfig(filename: string): Promise<LocalLLMConfig> {
    try {
      const config = await apiClient.config.getConfig('llm', filename);
      return this.mapToLocalLLMConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get LLM configuration ${filename}`);
      throw error;
    }
  }

  // Create new LLM configuration
  async createLLMConfig(filename: string, config: LocalLLMConfig): Promise<LocalLLMConfig> {
    try {
      const apiConfig = this.mapToApiLLMConfig(config);
      const result = await apiClient.config.createConfig('llm', apiConfig);
      return this.mapToLocalLLMConfig(result);
    } catch (error) {
      this.handleError(error, `Failed to create LLM configuration ${filename}`);
      throw error;
    }
  }

  // Update LLM configuration
  async updateLLMConfig(filename: string, config: LocalLLMConfig): Promise<LocalLLMConfig> {
    try {
      const apiConfig = this.mapToApiLLMConfig(config);
      const result = await apiClient.config.updateConfig('llm', filename, apiConfig);
      return this.mapToLocalLLMConfig(result);
    } catch (error) {
      this.handleError(error, `Failed to update LLM configuration ${filename}`);
      throw error;
    }
  }

  // Delete LLM configuration
  async deleteLLMConfig(filename: string): Promise<void> {
    try {
      await apiClient.config.deleteConfig('llm', filename);
    } catch (error) {
      this.handleError(error, `Failed to delete LLM configuration ${filename}`);
      throw error;
    }
  }

  // Register an LLM configuration (reload configs)
  async registerLLM(config: LocalLLMConfig): Promise<SuccessResponse> {
    try {
      await apiClient.config.reloadConfigs();
      return {
        status: 'success',
        message: `LLM ${config.llm_id} registered successfully`
      };
    } catch (error) {
      this.handleError(error, `Failed to register LLM ${config.llm_id}`);
      throw error;
    }
  }

  // Helper to generate a unique filename for LLM config
  generateConfigFilename(llmId: string): string {
    const sanitized = llmId.toLowerCase().replace(/[^a-z0-9]/g, '_');
    return `${sanitized}.json`;
  }

  // Create and register LLM in one operation
  async createAndRegisterLLM(config: LocalLLMConfig): Promise<{
    configFile: string;
    registration: SuccessResponse;
  }> {
    const filename = this.generateConfigFilename(config.llm_id);
    
    try {
      // First create the config file
      await this.createLLMConfig(filename, config);
      
      // Then register the LLM
      const registration = await this.registerLLM(config);
      
      return {
        configFile: filename,
        registration
      };
    } catch (error) {
      this.handleError(error, `Failed to create and register LLM ${config.llm_id}`);
      throw error;
    }
  }

  // Get common LLM presets
  getCommonPresets(): Partial<LocalLLMConfig>[] {
    return [
      {
        provider: 'openai',
        model: 'gpt-4',
        temperature: 0.7,
        max_tokens: 2048
      },
      {
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        temperature: 0.7,
        max_tokens: 2048
      },
      {
        provider: 'anthropic',
        model: 'claude-3-opus-20240229',
        temperature: 0.7,
        max_tokens: 4096
      },
      {
        provider: 'anthropic',
        model: 'claude-3-sonnet-20240229',
        temperature: 0.7,
        max_tokens: 4096
      },
      {
        provider: 'google',
        model: 'gemini-pro',
        temperature: 0.7,
        max_tokens: 2048
      }
    ];
  }

  // Validate LLM configuration
  validateConfig(config: Partial<LocalLLMConfig>): string[] {
    const errors: string[] = [];

    if (!config.llm_id) {
      errors.push('LLM ID is required');
    }

    if (!config.provider) {
      errors.push('Provider is required');
    }

    if (!config.model) {
      errors.push('Model is required');
    }

    if (config.temperature !== undefined) {
      if (config.temperature < 0 || config.temperature > 2) {
        errors.push('Temperature must be between 0 and 2');
      }
    }

    if (config.max_tokens !== undefined) {
      if (config.max_tokens < 1) {
        errors.push('Max tokens must be at least 1');
      }
    }

    return errors;
  }

  // Helper method to handle errors with user-friendly messages
  private handleError(error: unknown, context: string): void {
    if (error instanceof ApiError) {
      console.error(`${context}: ${error.getDisplayMessage()}`, error.toJSON());
    } else if (error instanceof TimeoutError) {
      console.error(`${context}: Request timed out`, error);
    } else if (error instanceof CancellationError) {
      console.error(`${context}: Request was cancelled`, error);
    } else {
      console.error(`${context}: Unknown error`, error);
    }
  }

  // Map API client LLMConfig to local LLMConfig
  private mapToLocalLLMConfig(apiConfig: any): LocalLLMConfig {
    return {
      llm_id: apiConfig.llm_id,
      provider: apiConfig.provider,
      model: apiConfig.model,
      api_key_env_var: apiConfig.api_key_env_var,
      default_system_prompt: apiConfig.default_system_prompt,
      max_tokens: apiConfig.max_tokens,
      temperature: apiConfig.temperature,
    };
  }

  // Map local LLMConfig to API client LLMConfig
  private mapToApiLLMConfig(localConfig: LocalLLMConfig): any {
    return {
      llm_id: localConfig.llm_id,
      provider: localConfig.provider,
      model: localConfig.model,
      api_key_env_var: localConfig.api_key_env_var,
      default_system_prompt: localConfig.default_system_prompt,
      max_tokens: localConfig.max_tokens,
      temperature: localConfig.temperature,
    };
  }
}

export default new LLMsService();
