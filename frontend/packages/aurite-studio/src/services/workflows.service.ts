import apiClient from './apiClient';
import { 
  WorkflowConfig,
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
  WorkflowExecutionResult,
} from '@aurite/api-client';

class WorkflowsService {
  // List all registered simple workflows
  async listWorkflows(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('simple_workflows');
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
      return await apiClient.config.listConfigs('simple_workflows');
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
      const config = await apiClient.config.getConfig('simple_workflow', id);
      return this.mapToLocalWorkflowConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get workflow configuration for ${id}`);
      throw error;
    }
  }

  // Get workflow configuration by filename
  async getWorkflowConfig(filename: string): Promise<WorkflowConfig> {
    try {
      const config = await apiClient.config.getConfig('simple_workflow', filename);
      return this.mapToLocalWorkflowConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get workflow configuration ${filename}`);
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

  // Create new workflow configuration
  async createWorkflowConfig(filename: string, config: WorkflowConfig): Promise<WorkflowConfig> {
    try {
      const apiConfig = this.mapToApiWorkflowConfig(config);
      const result = await apiClient.config.createConfig('simple_workflow', apiConfig);
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
      const result = await apiClient.config.updateConfig('simple_workflow', filename, apiConfig);
      return this.mapToLocalWorkflowConfig(result);
    } catch (error) {
      this.handleError(error, `Failed to update workflow configuration ${filename}`);
      throw error;
    }
  }

  // Delete workflow configuration
  async deleteWorkflowConfig(filename: string): Promise<void> {
    try {
      await apiClient.config.deleteConfig('simple_workflow', filename);
    } catch (error) {
      this.handleError(error, `Failed to delete workflow configuration ${filename}`);
      throw error;
    }
  }

  // Register a simple workflow (reload configs)
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

  // Execute a simple workflow
  async executeWorkflow(
    workflowName: string,
    request: ExecuteWorkflowRequest
  ): Promise<ExecuteWorkflowResponse> {
    try {
      const apiRequest: WorkflowRunRequest = {
        initial_input: request.initial_user_message,
      };
      
      const result: WorkflowExecutionResult = await apiClient.execution.runSimpleWorkflow(workflowName, apiRequest);
      
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
      
      const result: WorkflowExecutionResult = await apiClient.execution.runCustomWorkflow(workflowName, apiRequest);
      
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
      console.error(`${context}: ${error.getDisplayMessage()}`, error.toJSON());
    } else if (error instanceof TimeoutError) {
      console.error(`${context}: Request timed out`, error);
    } else if (error instanceof CancellationError) {
      console.error(`${context}: Request was cancelled`, error);
    } else {
      console.error(`${context}: Unknown error`, error);
    }
  }

  // Map API client WorkflowConfig to local WorkflowConfig
  private mapToLocalWorkflowConfig(apiConfig: any): WorkflowConfig {
    return {
      name: apiConfig.name,
      steps: apiConfig.steps,
      description: apiConfig.description,
    };
  }

  // Map local WorkflowConfig to API client WorkflowConfig
  private mapToApiWorkflowConfig(localConfig: WorkflowConfig): any {
    return {
      name: localConfig.name,
      steps: localConfig.steps,
      description: localConfig.description,
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

  // Map API client WorkflowExecutionResult to local ExecuteWorkflowResponse
  private mapToLocalWorkflowResponse(workflowName: string, apiResult: WorkflowExecutionResult): ExecuteWorkflowResponse {
    return {
      workflow_name: workflowName,
      status: apiResult.status === 'success' ? 'completed' : 'failed',
      final_message: apiResult.final_output?.toString(),
      error: apiResult.error_message || null,
    };
  }

  // Map API client WorkflowExecutionResult to local ExecuteCustomWorkflowResponse
  private mapToLocalCustomWorkflowResponse(workflowName: string, apiResult: WorkflowExecutionResult): ExecuteCustomWorkflowResponse {
    return {
      workflow_name: workflowName,
      status: apiResult.status === 'success' ? 'completed' : 'failed',
      result: apiResult.final_output,
      error: apiResult.error_message || null,
    };
  }
}

const workflowsService = new WorkflowsService();
export default workflowsService;
