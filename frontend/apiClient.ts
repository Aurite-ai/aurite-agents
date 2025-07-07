/**
 * Aurite API Client
 *
 * A TypeScript client for interacting with the Aurite Framework API.
 * Provides type-safe methods for all API endpoints.
 */

// Types
export interface ApiConfig {
  baseUrl: string;
  apiKey: string;
}

export interface AgentRunRequest {
  user_message: string;
  system_prompt?: string;
  session_id?: string;
}

export interface WorkflowRunRequest {
  initial_input: any;
  session_id?: string;
}

export interface AgentRunResult {
  status: 'success' | 'error' | 'max_iterations_reached';
  final_response?: {
    role: string;
    content: string;
  };
  conversation_history: Array<{
    role: string;
    content?: string;
    tool_calls?: any[];
  }>;
  error_message?: string;
}

export interface WorkflowExecutionResult {
  status: 'success' | 'error';
  steps: Array<{
    step_name: string;
    status: 'success' | 'error';
    result?: any;
    error?: string;
  }>;
  final_output?: any;
  error_message?: string;
}

export interface ToolCallArgs {
  args: Record<string, any>;
}

export interface ToolCallResult {
  content: Array<{
    type: string;
    text?: string;
  }>;
  isError?: boolean;
}

export interface ServerConfig {
  name: string;
  server_path?: string;
  command?: string;
  args?: string[];
  transport_type?: 'stdio' | 'local' | 'http_stream';
  http_endpoint?: string;
  headers?: Record<string, string>;
  capabilities?: string[];
  timeout?: number;
}

export interface StreamEvent {
  type: string;
  data: any;
}

// API Client Class
export class AuriteApiClient {
  private config: ApiConfig;

  constructor(config: ApiConfig) {
    this.config = config;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: any
  ): Promise<T> {
    const url = `${this.config.baseUrl}${path}`;
    const headers: HeadersInit = {
      'X-API-Key': this.config.apiKey,
      'Content-Type': 'application/json',
    };

    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `API request failed: ${response.status}`);
    }

    return response.json();
  }

  // Execution Facade API
  async getExecutionStatus(): Promise<{ status: string }> {
    return this.request('GET', '/execution/status');
  }

  async runAgent(agentName: string, request: AgentRunRequest): Promise<AgentRunResult> {
    return this.request('POST', `/execution/agents/${encodeURIComponent(agentName)}/run`, request);
  }

  async streamAgent(
    agentName: string,
    request: AgentRunRequest,
    onEvent: (event: StreamEvent) => void
  ): Promise<void> {
    const url = `${this.config.baseUrl}/execution/agents/${encodeURIComponent(agentName)}/stream`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'X-API-Key': this.config.apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Stream request failed: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            onEvent(event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  }

  async runSimpleWorkflow(
    workflowName: string,
    request: WorkflowRunRequest
  ): Promise<WorkflowExecutionResult> {
    return this.request(
      'POST',
      `/execution/workflows/simple/${encodeURIComponent(workflowName)}/run`,
      request
    );
  }

  async runCustomWorkflow(
    workflowName: string,
    request: WorkflowRunRequest
  ): Promise<any> {
    return this.request(
      'POST',
      `/execution/workflows/custom/${encodeURIComponent(workflowName)}/run`,
      request
    );
  }

  // MCP Host API
  async getHostStatus(): Promise<{ status: string; tool_count: number }> {
    return this.request('GET', '/host/status');
  }

  async listTools(): Promise<Array<{
    name: string;
    description?: string;
    inputSchema: any;
  }>> {
    return this.request('GET', '/host/tools');
  }

  async registerServerByName(serverName: string): Promise<{ status: string; name: string }> {
    return this.request('POST', `/host/register/${encodeURIComponent(serverName)}`);
  }

  async registerServerByConfig(config: ServerConfig): Promise<{ status: string; name: string }> {
    return this.request('POST', '/host/register/config', config);
  }

  async unregisterServer(serverName: string): Promise<{ status: string; name: string }> {
    return this.request('DELETE', `/host/servers/${encodeURIComponent(serverName)}`);
  }

  async callTool(toolName: string, args: Record<string, any>): Promise<ToolCallResult> {
    return this.request('POST', `/host/tools/${encodeURIComponent(toolName)}/call`, { args });
  }

  // Config Manager API
  async listConfigs(configType: string): Promise<string[]> {
    return this.request('GET', `/config/${configType}`);
  }

  async getConfig(configType: string, name: string): Promise<any> {
    return this.request('GET', `/config/${configType}/${encodeURIComponent(name)}`);
  }

  async createConfig(configType: string, config: any): Promise<{ message: string }> {
    return this.request('POST', `/config/${configType}`, config);
  }

  async updateConfig(configType: string, name: string, config: any): Promise<{ message: string }> {
    return this.request('PUT', `/config/${configType}/${encodeURIComponent(name)}`, config);
  }

  async deleteConfig(configType: string, name: string): Promise<{ message: string }> {
    return this.request('DELETE', `/config/${configType}/${encodeURIComponent(name)}`);
  }

  async reloadConfigs(): Promise<{ message: string }> {
    return this.request('POST', '/config/reload');
  }
}

// Export a factory function for convenience
export function createAuriteClient(baseUrl: string, apiKey: string): AuriteApiClient {
  return new AuriteApiClient({ baseUrl, apiKey });
}
