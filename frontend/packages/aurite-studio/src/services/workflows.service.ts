import apiClient from './apiClient';
import {
  WorkflowConfig,
  WorkflowDisplayModel,
  CustomWorkflowConfig,
  ExecuteWorkflowRequest,
  ExecuteCustomWorkflowRequest,
  ExecuteWorkflowResponse,
  ExecuteCustomWorkflowResponse,
  SuccessResponse
} from '../types';
import {
  ApiError,
  TimeoutError,
  CancellationError,
  WorkflowRunRequest,
} from '@aurite-ai/api-client';

class WorkflowsService {
  // List all registered linear workflows
  async listWorkflows(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('linear_workflows');
    } catch (error) {
      this.handleError(error, 'Failed to list workflows');
      throw error;
    }
  }

  // List all registered custom workflows
  async listCustomWorkflows(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('custom_workflows');
    } catch (error) {
      this.handleError(error, 'Failed to list custom workflows');
      throw error;
    }
  }

  // List workflow configuration files
  async listWorkflowConfigs(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('linear_workflows');
    } catch (error) {
      this.handleError(error, 'Failed to list workflow configurations');
      throw error;
    }
  }

  // List custom workflow configuration files
  async listCustomWorkflowConfigs(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('custom_workflows');
    } catch (error) {
      this.handleError(error, 'Failed to list custom workflow configurations');
      throw error;
    }
  }

  // Get workflow configuration by ID
  async getWorkflowById(id: string): Promise<WorkflowConfig> {
    try {
      const config = await apiClient.config.getConfig('linear_workflow', id);
      return this.mapToLocalWorkflowConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get workflow configuration for ${id}`);
      throw error;
    }
  }

  // Get workflow configuration by filename
  async getWorkflowConfig(filename: string): Promise<WorkflowConfig> {
    try {
      const config = await apiClient.config.getConfig('linear_workflow', filename);
      return this.mapToLocalWorkflowConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get workflow configuration ${filename}`);
      throw error;
    }
  }

  // Get workflow configuration by name (for editing) - similar to LLM config pattern
  async getWorkflowConfigByName(workflowName: string): Promise<WorkflowConfig> {
    try {
      const config = await apiClient.config.getConfig('linear_workflow', workflowName);
      return this.mapToLocalWorkflowConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get workflow configuration for ${workflowName}`);
      throw error;
    }
  }

  // Get custom workflow configuration by filename
  async getCustomWorkflowConfig(filename: string): Promise<CustomWorkflowConfig> {
    try {
      const config = await apiClient.config.getConfig('custom_workflow', filename);
      return this.mapToLocalCustomWorkflowConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get custom workflow configuration ${filename}`);
      throw error;
    }
  }

  // Get custom workflow configuration by name (for editing)
  async getCustomWorkflowConfigByName(workflowName: string): Promise<CustomWorkflowConfig> {
    try {
      const config = await apiClient.config.getConfig('custom_workflow', workflowName);
      return this.mapToLocalCustomWorkflowConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get custom workflow configuration for ${workflowName}`);
      throw error;
    }
  }

  // Create new workflow configuration
  async createWorkflowConfig(filename: string, config: WorkflowConfig): Promise<WorkflowConfig> {
    try {
      const apiConfig = this.mapToApiWorkflowConfig(config);
      const result = await apiClient.config.createConfig('linear_workflow', apiConfig);
      return this.mapToLocalWorkflowConfig(result);
    } catch (error) {
      this.handleError(error, `Failed to create workflow configuration ${filename}`);
      throw error;
    }
  }

  // Update workflow configuration
  async updateWorkflowConfig(filename: string, config: WorkflowConfig): Promise<WorkflowConfig> {
    try {
      const apiConfig = this.mapToApiWorkflowConfig(config);
      const result = await apiClient.config.updateConfig('linear_workflow', filename, apiConfig);
      return this.mapToLocalWorkflowConfig(result);
    } catch (error) {
      this.handleError(error, `Failed to update workflow configuration ${filename}`);
      throw error;
    }
  }

  // Update custom workflow configuration
  async updateCustomWorkflowConfig(filename: string, config: CustomWorkflowConfig): Promise<CustomWorkflowConfig> {
    try {
      const apiConfig = this.mapToApiCustomWorkflowConfig(config);
      const result = await apiClient.config.updateConfig('custom_workflow', filename, apiConfig);
      return this.mapToLocalCustomWorkflowConfig(result);
    } catch (error) {
      this.handleError(error, `Failed to update custom workflow configuration ${filename}`);
      throw error;
    }
  }

  // Delete workflow configuration
  async deleteWorkflowConfig(filename: string): Promise<void> {
    try {
      await apiClient.config.deleteConfig('linear_workflow', filename);
    } catch (error) {
      this.handleError(error, `Failed to delete workflow configuration ${filename}`);
      throw error;
    }
  }

  // Delete custom workflow configuration
  async deleteCustomWorkflowConfig(filename: string): Promise<void> {
    try {
      await apiClient.config.deleteConfig('custom_workflow', filename);
    } catch (error) {
      this.handleError(error, `Failed to delete custom workflow configuration ${filename}`);
      throw error;
    }
  }

  // Register a linear workflow (reload configs)
  async registerWorkflow(config: WorkflowConfig): Promise<SuccessResponse> {
    try {
      await apiClient.config.reloadConfigs();
      return {
        status: 'success',
        message: `Workflow ${config.name} registered successfully`
      };
    } catch (error) {
      this.handleError(error, `Failed to register workflow ${config.name}`);
      throw error;
    }
  }

  // Register a custom workflow (reload configs)
  async registerCustomWorkflow(config: CustomWorkflowConfig): Promise<SuccessResponse> {
    try {
      await apiClient.config.reloadConfigs();
      return {
        status: 'success',
        message: `Custom workflow ${config.name} registered successfully`
      };
    } catch (error) {
      this.handleError(error, `Failed to register custom workflow ${config.name}`);
      throw error;
    }
  }

  // Execute a linear workflow
  async executeWorkflow(
    workflowName: string,
    request: ExecuteWorkflowRequest
  ): Promise<ExecuteWorkflowResponse> {
    try {
      const apiRequest: WorkflowRunRequest = {
        initial_input: request.initial_input,
        session_id: request.session_id,
      };

      const result = await apiClient.execution.runLinearWorkflow(workflowName, apiRequest);

      return this.mapToLocalWorkflowResponse(workflowName, result);
    } catch (error) {
      this.handleError(error, `Failed to execute workflow ${workflowName}`);
      throw error;
    }
  }

  // Execute a custom workflow
  async executeCustomWorkflow(
    workflowName: string,
    request: ExecuteCustomWorkflowRequest
  ): Promise<ExecuteCustomWorkflowResponse> {
    try {
      const apiRequest: WorkflowRunRequest = {
        initial_input: request.initial_input,
      };

      const result = await apiClient.execution.runCustomWorkflow(workflowName, apiRequest);

      return this.mapToLocalCustomWorkflowResponse(workflowName, result);
    } catch (error) {
      this.handleError(error, `Failed to execute custom workflow ${workflowName}`);
      throw error;
    }
  }

  // Helper to generate a unique filename for workflow config
  generateConfigFilename(workflowName: string): string {
    const sanitized = workflowName.toLowerCase().replace(/[^a-z0-9]/g, '_');
    return `${sanitized}.json`;
  }

  // Create new custom workflow configuration
  async createCustomWorkflowConfig(config: CustomWorkflowConfig): Promise<CustomWorkflowConfig> {
    try {
      const apiConfig = this.mapToApiCustomWorkflowConfig(config);
      const result = await apiClient.config.createConfig('custom_workflow', apiConfig);
      return this.mapToLocalCustomWorkflowConfig(result);
    } catch (error) {
      this.handleError(error, `Failed to create custom workflow configuration`);
      throw error;
    }
  }

  // Create and register custom workflow in one operation
  async createAndRegisterCustomWorkflow(config: CustomWorkflowConfig): Promise<{
    configFile: string;
    registration: SuccessResponse;
  }> {
    const filename = this.generateConfigFilename(config.name);

    try {
      // First create the config file
      await this.createCustomWorkflowConfig(config);

      // Then register the custom workflow
      const registration = await this.registerCustomWorkflow(config);

      return {
        configFile: filename,
        registration
      };
    } catch (error) {
      this.handleError(error, `Failed to create and register custom workflow ${config.name}`);
      throw error;
    }
  }

  // Create and register workflow in one operation
  async createAndRegisterWorkflow(config: WorkflowConfig): Promise<{
    configFile: string;
    registration: SuccessResponse;
  }> {
    const filename = this.generateConfigFilename(config.name);

    try {
      // First create the config file
      await this.createWorkflowConfig(filename, config);

      // Then register the workflow
      const registration = await this.registerWorkflow(config);

      return {
        configFile: filename,
        registration
      };
    } catch (error) {
      this.handleError(error, `Failed to create and register workflow ${config.name}`);
      throw error;
    }
  }

  // Helper method to handle errors with user-friendly messages
  private handleError(error: unknown, context: string): void {
    if (error instanceof ApiError) {
      console.error('%s: %s', context, String(error.getDisplayMessage()), error.toJSON());
    } else if (error instanceof TimeoutError) {
      console.error('%s: Request timed out', context, error);
    } else if (error instanceof CancellationError) {
      console.error('%s: Request was cancelled', context, error);
    } else {
      console.error('%s: Unknown error', context, error);
    }
  }

  // Map API client WorkflowConfig to local WorkflowConfig
  private mapToLocalWorkflowConfig(apiConfig: any): WorkflowConfig {
    return {
      name: apiConfig.name,
      type: "linear_workflow",
      steps: apiConfig.steps || [],
      description: apiConfig.description,
    };
  }

  // Map local WorkflowConfig to API client WorkflowConfig
  private mapToApiWorkflowConfig(localConfig: WorkflowConfig): any {
    return {
      name: localConfig.name,
      type: "linear_workflow",
      steps: localConfig.steps || [],
      description: localConfig.description,
    };
  }

  // Helper to create WorkflowDisplayModel from WorkflowConfig
  private createDisplayModel(config: WorkflowConfig, configFile?: string): WorkflowDisplayModel {
    const stepCount = config.steps?.length || 0;
    const stepPreview = stepCount > 0
      ? config.steps.slice(0, 3).join(' → ') + (stepCount > 3 ? ' ...' : '')
      : 'No steps configured';

    return {
      name: config.name,
      description: config.description,
      stepCount,
      stepPreview,
      type: 'linear_workflow',
      status: 'active',
      configFile,
    };
  }

  // Map API client CustomWorkflowConfig to local CustomWorkflowConfig
  private mapToLocalCustomWorkflowConfig(apiConfig: any): CustomWorkflowConfig {
    return {
      name: apiConfig.name,
      class_name: apiConfig.class_name,
      module_path: apiConfig.module_path,
      description: apiConfig.description,
    };
  }

  // Map local CustomWorkflowConfig to API client CustomWorkflowConfig
  private mapToApiCustomWorkflowConfig(localConfig: CustomWorkflowConfig): any {
    return {
      name: localConfig.name,
      type: "custom_workflow",
      class_name: localConfig.class_name,
      module_path: localConfig.module_path,
      description: localConfig.description,
    };
  }

  // Map API client WorkflowExecutionResult to local ExecuteWorkflowResponse
  private mapToLocalWorkflowResponse(workflowName: string, apiResult: any): ExecuteWorkflowResponse {
    return {
      workflow_name: workflowName,
      status: apiResult.status === 'completed' ? 'completed' : 'failed',
      final_message: apiResult.final_output?.toString(),
      error: apiResult.error || null,
    };
  }

  // Map API client WorkflowExecutionResult to local ExecuteCustomWorkflowResponse
  private mapToLocalCustomWorkflowResponse(workflowName: string, apiResult: any): ExecuteCustomWorkflowResponse {
    // Handle the actual API response format from custom workflow execution
    // Backend returns: { status: "ok", response: "..." } for success
    // Backend returns: { status: "error", error: "..." } for failure

    const isSuccess = apiResult.status === 'ok' || apiResult.status === 'completed';

    return {
      workflow_name: workflowName,
      status: isSuccess ? 'completed' : 'failed',
      result: apiResult.response || apiResult.final_output || apiResult.result,
      error: apiResult.error || null,
    };
  }
}

const workflowsService = new WorkflowsService();
export default workflowsService;
