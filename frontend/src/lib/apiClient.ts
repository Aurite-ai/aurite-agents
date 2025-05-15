import useAuthStore from '../store/authStore';

// Allow body to be an object, which we'll stringify
interface ApiClientOptions extends Omit<RequestInit, 'body'> {
  body?: BodyInit | null | Record<string, any>; // Allow object for body
  // We can add other custom options here if needed in the future
}

const apiClient = async (
  url: string,
  options: ApiClientOptions = {}
): Promise<Response> => {
  const { apiKey, clearAuth } = useAuthStore.getState();
  let processedBody = options.body;

  const headers = new Headers(options.headers || {});
  if (apiKey) {
    headers.append('X-API-Key', apiKey);
  }

  // Ensure Content-Type is set for POST/PUT if body is an object (common case)
  // and stringify the body.
  if (processedBody && typeof processedBody === 'object' &&
      !(processedBody instanceof Blob) && !(processedBody instanceof FormData) && !(processedBody instanceof URLSearchParams) && !(typeof ReadableStream !== 'undefined' && processedBody instanceof ReadableStream)) {
    if (!headers.has('Content-Type')) {
      headers.append('Content-Type', 'application/json');
    }
    // Only stringify if Content-Type is application/json
    if (headers.get('Content-Type')?.includes('application/json')) {
      processedBody = JSON.stringify(processedBody);
    }
  }

  const fetchOptions: RequestInit = {
    ...options,
    headers,
    body: processedBody as BodyInit | null | undefined, // Cast after processing
  };

  // Use a relative URL if it doesn't start with http, otherwise use it as is.
  // This helps if some URLs might be absolute (e.g. to external services in future)
  // For now, all our API calls are relative to the same origin.
  const requestUrl = url.startsWith('http') ? url : `/api${url.startsWith('/') ? url : `/${url}`}`;


  try {
    const response = await fetch(requestUrl, fetchOptions);

    if (response.status === 401) {
      // Unauthorized: API key might be invalid or expired
      console.warn('API request unauthorized (401). Clearing auth state.');
      clearAuth(); // This will trigger the ApiKeyModal to show via App.tsx logic
      // We might want to throw a specific error or return a custom response
      // to let the caller know authentication failed and was handled.
      // For now, clearAuth handles the UI part.
      // Rethrowing or returning a specific marker could allow callers to avoid further processing.
      throw new Error('Unauthorized - API Key rejected or missing.');
    }

    return response;
  } catch (error) {
    // Handle network errors or the rethrown 401 error
    console.error('API Client Error:', error);
    // Ensure the error is re-thrown so the caller can handle it if needed
    // If it was a 401, clearAuth has already been called.
    throw error;
  }
};

export default apiClient;

// Add to frontend/src/lib/apiClient.ts
import type { ProjectConfig, LoadComponentsResponse, ApiError } from '../types/projectManagement'; // Adjust path

// ... (existing apiClient code)

export async function createProjectFile(
  filename: string,
  projectName: string,
  projectDescription?: string
): Promise<ProjectConfig> { // Assuming backend returns the full ProjectConfig on success
  const response = await apiClient('/projects/create_file', {
    method: 'POST',
    body: { filename, project_name: projectName, project_description: projectDescription },
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to create project file', status: response.status, details: errorData } as ApiError;
  }
  return response.json() as Promise<ProjectConfig>;
}

export async function loadProjectComponents(
  projectConfigPath: string
): Promise<LoadComponentsResponse> {
  const response = await apiClient('/projects/load_components', {
    method: 'POST',
    body: { project_config_path: projectConfigPath },
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to load project components', status: response.status, details: errorData } as ApiError;
  }
  return response.json() as Promise<LoadComponentsResponse>;
}

export async function listProjectFiles(): Promise<string[]> {
  const response = await apiClient('/projects/list_files', {
    method: 'GET',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to list project files', status: response.status, details: errorData } as ApiError;
  }
  return response.json() as Promise<string[]>;
}

// --- Generic Config File Management ---

export async function listConfigFiles(componentType: string): Promise<string[]> {
  let url = '';
  let apiPathType = componentType;
  if (componentType === 'projects') {
    url = '/projects/list_files';
  } else {
    if (componentType === 'llms') {
      apiPathType = 'llms';
    } else if (componentType === 'simple_workflows') {
      apiPathType = 'simple-workflows';
    } else if (componentType === 'custom_workflows') {
      apiPathType = 'custom-workflows';
    }
    url = `/configs/${apiPathType}`;
  }
  const response = await apiClient(url, { method: 'GET' });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || `Failed to list ${componentType} files`, status: response.status, details: errorData } as ApiError;
  }
  return response.json() as Promise<string[]>;
}

export async function getConfigFileContent(componentType: string, filename: string): Promise<any> {
  let url = '';
  let apiPathType = componentType;
  if (componentType === 'projects') {
    url = `/projects/file/${filename}`;
  } else {
    if (componentType === 'llms') {
      apiPathType = 'llms';
    } else if (componentType === 'simple_workflows') {
      apiPathType = 'simple-workflows';
    } else if (componentType === 'custom_workflows') {
      apiPathType = 'custom-workflows';
    }
    url = `/configs/${apiPathType}/${filename}`;
  }
  const response = await apiClient(url, { method: 'GET' });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || `Failed to get ${filename}`, status: response.status, details: errorData } as ApiError;
  }
  return response.json(); // Returns raw JSON content (object or array)
}

export async function saveConfigFileContent(componentType: string, filename: string, content: any): Promise<any> {
  let url = '';
  let apiPathType = componentType;
  if (componentType === 'projects') {
    url = `/projects/file/${filename}`;
  } else {
    if (componentType === 'llms') {
      apiPathType = 'llms';
    } else if (componentType === 'simple_workflows') {
      apiPathType = 'simple-workflows';
    } else if (componentType === 'custom_workflows') {
      apiPathType = 'custom-workflows';
    }
    url = `/configs/${apiPathType}/${filename}`;
  }
  const response = await apiClient(url, {
    method: 'PUT',
    body: { content }, // Backend expects { "content": ... }
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || `Failed to save ${filename}`, status: response.status, details: errorData } as ApiError;
  }
  return response.json(); // Or a success message/status
}

export async function getSpecificComponentConfig(componentType: string, idOrName: string): Promise<any> {
  let apiPathType = componentType;
  if (componentType === 'llms') {
    apiPathType = 'llms';
  } else if (componentType === 'simple_workflows') {
    apiPathType = 'simple-workflows';
  } else if (componentType === 'custom_workflows') {
    apiPathType = 'custom-workflows';
  }
  // For 'agents' and 'clients', componentType can be used directly as apiPathType.
  // 'projects' type is not applicable here as project files are not fetched by individual ID through this generic component mechanism.

  const encodedIdOrName = encodeURIComponent(idOrName);
  const url = `/configs/${apiPathType}/id/${encodedIdOrName}`;

  const response = await apiClient(url, { method: 'GET' });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || `Failed to get ${componentType} config for ${idOrName}`, status: response.status, details: errorData } as ApiError;
  }
  return response.json();
}

// --- Execution Tab API Functions ---

// Import specific types for better type safety
import type {
  AgentConfig,
  LLMConfig,
  AgentExecutionResult,
  CustomWorkflowConfig,
  ExecuteCustomWorkflowResponse,
  WorkflowConfig, // Added
  ExecuteWorkflowResponse // Added
} from '../types/projectManagement'; // Ensure these are exported

export async function listRegisteredAgents(): Promise<string[]> {
  const response = await apiClient('/components/agents', { method: 'GET' });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to list registered agents', status: response.status, details: errorData } as ApiError;
  }
  return response.json() as Promise<string[]>;
}

export async function listRegisteredSimpleWorkflows(): Promise<string[]> {
  const response = await apiClient('/components/workflows', { method: 'GET' });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to list registered simple workflows', status: response.status, details: errorData } as ApiError;
  }
  return response.json() as Promise<string[]>;
}

export async function listRegisteredCustomWorkflows(): Promise<string[]> {
  const response = await apiClient('/components/custom_workflows', { method: 'GET' });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to list registered custom workflows', status: response.status, details: errorData } as ApiError;
  }
  return response.json() as Promise<string[]>;
}

export async function registerLlmConfigAPI(llmConfig: LLMConfig): Promise<any> { // Changed type from any
  const response = await apiClient('/llms/register', {
    method: 'POST',
    body: llmConfig, // The whole llmConfig object is the body
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to register LLM config', status: response.status, details: errorData } as ApiError;
  }
  return response.json();
}

export async function registerAgentAPI(agentConfig: AgentConfig): Promise<any> { // Changed type from any
  const response = await apiClient('/agents/register', {
    method: 'POST',
    body: agentConfig, // The whole agentConfig object is the body
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to register agent', status: response.status, details: errorData } as ApiError;
  }
  return response.json();
}

export async function executeAgentAPI(agentName: string, userMessage: string, systemPrompt?: string): Promise<AgentExecutionResult> { // Changed return type from any
  const response = await apiClient(`/agents/${agentName}/execute`, {
    method: 'POST',
    body: { user_message: userMessage, system_prompt: systemPrompt },
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || `Failed to execute agent ${agentName}`, status: response.status, details: errorData } as ApiError;
  }
  return response.json();
}

export async function registerCustomWorkflowAPI(customWorkflowConfig: CustomWorkflowConfig): Promise<any> {
  const response = await apiClient('/custom_workflows/register', {
    method: 'POST',
    body: customWorkflowConfig,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to register custom workflow', status: response.status, details: errorData } as ApiError;
  }
  return response.json();
}

export async function executeCustomWorkflowAPI(workflowName: string, initialInput: any): Promise<ExecuteCustomWorkflowResponse> {
  const encodedWorkflowName = encodeURIComponent(workflowName);
  const response = await apiClient(`/custom_workflows/${encodedWorkflowName}/execute`, {
    method: 'POST',
    body: { initial_input: initialInput },
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || `Failed to execute custom workflow ${workflowName}`, status: response.status, details: errorData } as ApiError;
  }
  return response.json();
}

export async function registerSimpleWorkflowAPI(workflowConfig: WorkflowConfig): Promise<any> {
  const response = await apiClient('/workflows/register', {
    method: 'POST',
    body: workflowConfig,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to register simple workflow', status: response.status, details: errorData } as ApiError;
  }
  return response.json();
}

export async function executeSimpleWorkflowAPI(workflowName: string, initialUserMessage: string): Promise<ExecuteWorkflowResponse> {
  const encodedWorkflowName = encodeURIComponent(workflowName);
  const response = await apiClient(`/workflows/${encodedWorkflowName}/execute`, {
    method: 'POST',
    body: { initial_user_message: initialUserMessage },
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || `Failed to execute simple workflow ${workflowName}`, status: response.status, details: errorData } as ApiError;
  }
  return response.json();
}

export async function getActiveProjectComponentConfig(projectComponentType: string, componentName: string): Promise<any> {
  const encodedComponentName = encodeURIComponent(componentName);
  // Ensure projectComponentType matches the expected path segments like "agents", "simple_workflows", etc.
  const url = `/projects/active/component/${projectComponentType}/${encodedComponentName}`;

  const response = await apiClient(url, { method: 'GET' });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || `Failed to get active project component ${componentName} of type ${projectComponentType}`, status: response.status, details: errorData } as ApiError;
  }
  return response.json();
}

export async function saveNewConfigFile(componentApiType: string, filename: string, configData: object): Promise<any> {
  // componentApiType should be the direct path segment expected by the backend API
  // e.g., "agents", "llms", "simple-workflows", "custom-workflows", "clients"
  const encodedFilename = encodeURIComponent(filename);
  const url = `/configs/${componentApiType}/${encodedFilename}`;

  const response = await apiClient(url, {
    method: 'POST',
    body: { content: configData }, // Backend's create_config_file expects { "content": ... }
  });

  if (!response.ok) {
    // Specific check for 409 Conflict (File Exists) might be useful if backend returns it distinctly
    // For now, general error handling:
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || `Failed to save config file ${filename}`, status: response.status, details: errorData } as ApiError;
  }
  return response.json(); // Assuming backend returns the created/saved config or a success message
}

export async function getActiveProjectFullConfig(): Promise<ProjectConfig> {
  const response = await apiClient('/projects/get_active_project_config', { method: 'GET' });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to get active project configuration', status: response.status, details: errorData } as ApiError;
  }
  return response.json() as Promise<ProjectConfig>;
}

export function streamAgentExecution(
  agentName: string,
  userMessage: string,
  systemPrompt?: string
): EventSource {
  const { apiKey } = useAuthStore.getState();
  const encodedAgentName = encodeURIComponent(agentName);
  const baseUrl = `/api/agents/${encodedAgentName}/execute-stream`;

  const params = new URLSearchParams();
  params.append('user_message', userMessage);

  if (systemPrompt) {
    params.append('system_prompt', systemPrompt);
  }

  if (apiKey) {
    params.append('api_key', apiKey);
  } else {
    console.warn(
      'API key is missing. Agent streaming request might fail.'
    );
  }

  const fullUrl = `${baseUrl}?${params.toString()}`;
  return new EventSource(fullUrl);
}

export async function listActiveHostClients(): Promise<string[]> {
  const response = await apiClient('/host/clients/active', { method: 'GET' });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw { message: errorData.detail || errorData.message || 'Failed to list active host clients', status: response.status, details: errorData } as ApiError;
  }
  return response.json() as Promise<string[]>;
}

export async function registerClientAPI(clientConfig: any): Promise<any> { // Using 'any' for now, refine with ClientConfig if available
  const response = await apiClient('/clients/register', {
    method: 'POST',
    body: clientConfig,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    // Try to access errorData.detail for FastAPI's common error structure
    throw { message: errorData.detail || errorData.message || 'Failed to register client', status: response.status, details: errorData } as ApiError;
  }
  return response.json();
}

// TODO: Add listRegisteredSimpleWorkflows etc. when needed
