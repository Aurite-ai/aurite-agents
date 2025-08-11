/**
 * Client for the Execution Facade API endpoints
 *
 * The Execution Facade provides a unified interface for running:
 * - Agents: AI-powered assistants that can use tools and maintain conversation history
 * - Linear Workflows: Sequential execution of multiple agents
 * - Custom Workflows: Python-based workflows with custom logic
 *
 * All execution happens server-side, with results returned to the client.
 */

import { BaseClient } from '../client/BaseClient';
import type {
  AgentRunRequest,
  AgentRunResult,
  WorkflowRunRequest,
  WorkflowExecutionResult,
  StreamEvent,
  LLMTestResult,
} from '../types';

export class ExecutionFacadeClient extends BaseClient {
  /**
   * Get the status of the Execution Facade
   *
   * @returns Status information about the execution facade
   * @example
   * ```typescript
   * const status = await client.execution.getStatus();
   * console.log(status); // { status: 'active' }
   * ```
   */
  async getStatus(): Promise<{ status: string }> {
    return this.request('GET', '/execution/status');
  }

  /**
   * Run an agent and wait for the complete response
   *
   * Agents are AI assistants that can:
   * - Process user messages
   * - Use configured MCP tools
   * - Maintain conversation history across sessions
   * - Follow custom system prompts
   *
   * @param agentName - Name of the configured agent to run
   * @param request - Request containing the user message and optional parameters
   * @returns Complete execution result including final response and conversation history
   * @throws Error if the agent is not found or execution fails
   *
   * @example
   * ```typescript
   * const result = await client.execution.runAgent('Weather Agent', {
   *   user_message: 'What is the weather in San Francisco?',
   *   session_id: 'user-123' // Optional: maintain conversation history
   * });
   *
   * console.log(result.final_response?.content);
   * // "The weather in San Francisco is sunny and 72°F..."
   * ```
   */
  async runAgent(agentName: string, request: AgentRunRequest): Promise<AgentRunResult> {
    return this.request('POST', `/execution/agents/${encodeURIComponent(agentName)}/run`, request);
  }

  /**
   * Stream an agent's response in real-time
   *
   * This method establishes a Server-Sent Events (SSE) connection to stream:
   * - LLM responses as they're generated
   * - Tool calls and their results
   * - Status updates and errors
   *
   * Useful for providing real-time feedback in chat interfaces.
   *
   * @param agentName - Name of the configured agent to run
   * @param request - Request containing the user message and optional parameters
   * @param onEvent - Callback function called for each streaming event
   * @throws Error if the stream connection fails
   *
   * @example
   * ```typescript
   * await client.execution.streamAgent(
   *   'Weather Agent',
   *   { user_message: 'Tell me about the weather' },
   *   (event) => {
   *     switch (event.type) {
   *       case 'llm_response':
   *         process.stdout.write(event.data.content); // Stream text as it arrives
   *         break;
   *       case 'tool_call':
   *         console.log(`Calling tool: ${event.data.name}`);
   *         break;
   *       case 'error':
   *         console.error(`Error: ${event.data.message}`);
   *         break;
   *     }
   *   }
   * );
   * ```
   */
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

    let reading = true;
    while (reading) {
      const { done, value } = await reader.read();
      if (done) {
        reading = false;
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            onEvent(event);
          } catch {
            // Silently ignore malformed SSE events
          }
        }
      }
    }
  }

  /**
   * Run a linear workflow (sequential agent execution)
   *
   * Linear workflows execute a series of agents in sequence, where:
   * - Each agent receives the output of the previous agent
   * - The workflow stops if any agent fails
   * - The final output is from the last agent in the sequence
   *
   * @param workflowName - Name of the configured linear workflow
   * @param request - Request containing the initial input for the workflow
   * @returns Execution result with details about each step
   * @throws Error if the workflow is not found or execution fails
   *
   * @example
   * ```typescript
   * const result = await client.execution.runLinearWorkflow(
   *   'Weather Planning Workflow',
   *   { initial_input: 'What should I wear in London today?' }
   * );
   *
   * // Check each step's result
   * result.steps.forEach(step => {
   *   console.log(`${step.step_name}: ${step.status}`);
   * });
   * ```
   */
  async runLinearWorkflow(
    workflowName: string,
    request: WorkflowRunRequest
  ): Promise<WorkflowExecutionResult> {
    return this.request(
      'POST',
      `/execution/workflows/linear/${encodeURIComponent(workflowName)}/run`,
      request
    );
  }

  /**
   * Run a custom workflow (Python-based with custom logic)
   *
   * Custom workflows are Python classes that can:
   * - Implement complex branching logic
   * - Call multiple agents conditionally
   * - Process and transform data between steps
   * - Integrate with external systems
   *
   * The return type depends on the specific workflow implementation.
   *
   * @param workflowName - Name of the configured custom workflow
   * @param request - Request containing the initial input for the workflow
   * @returns Workflow-specific output (type depends on the workflow)
   * @throws Error if the workflow is not found or execution fails
   *
   * @example
   * ```typescript
   * const result = await client.execution.runCustomWorkflow(
   *   'DataProcessingWorkflow',
   *   {
   *     initial_input: {
   *       data: [1, 2, 3],
   *       operation: 'sum'
   *     }
   *   }
   * );
   * ```
   */
  async runCustomWorkflow(workflowName: string, request: WorkflowRunRequest): Promise<any> {
    return this.request(
      'POST',
      `/execution/workflows/custom/${encodeURIComponent(workflowName)}/run`,
      request
    );
  }

  /**
   * Test an LLM configuration by running a simple validation call
   *
   * This method validates that an LLM configuration is working correctly by:
   * - Checking the configuration structure
   * - Testing connectivity to the LLM provider
   * - Validating API credentials
   * - Performing a simple test call
   *
   * @param llmConfigId - ID of the LLM configuration to test
   * @returns Test result with status and metadata or error details
   * @throws Error if the request fails or the LLM configuration is not found
   *
   * @example
   * ```typescript
   * try {
   *   const result = await client.execution.testLLM('my_openai_gpt4');
   *   if (result.status === 'success') {
   *     console.log(`LLM test passed: ${result.metadata?.provider}/${result.metadata?.model}`);
   *   } else {
   *     console.error(`LLM test failed: ${result.error?.message}`);
   *   }
   * } catch (error) {
   *   console.error('LLM test request failed:', error);
   * }
   * ```
   */
  async testLLM(llmConfigId: string): Promise<LLMTestResult> {
    return this.request('POST', `/execution/llms/${encodeURIComponent(llmConfigId)}/test`);
  }

  async testAgent(agentName: string): Promise<{ status: string }> {
    return this.request('POST', `/execution/agents/${encodeURIComponent(agentName)}/test`);
  }

  async testLinearWorkflow(workflowName: string): Promise<{ status: string }> {
    return this.request(
      'POST',
      `/execution/workflows/linear/${encodeURIComponent(workflowName)}/test`
    );
  }

  async testCustomWorkflow(workflowName: string): Promise<{ status: string }> {
    return this.request(
      'POST',
      `/execution/workflows/custom/${encodeURIComponent(workflowName)}/test`
    );
  }

  async validateCustomWorkflow(workflowName: string): Promise<{ status: string }> {
    return this.request(
      'POST',
      `/execution/workflows/custom/${encodeURIComponent(workflowName)}/validate`
    );
  }

  async getAgentHistory(agentName: string): Promise<any> {
    return this.request('GET', `/execution/agents/${encodeURIComponent(agentName)}/history`);
  }

  async getWorkflowHistory(workflowName: string): Promise<any> {
    return this.request('GET', `/execution/workflows/${encodeURIComponent(workflowName)}/history`);
  }

  async getAllHistory(): Promise<any> {
    return this.request('GET', '/execution/history');
  }

  async getHistoryBySessionId(sessionId: string): Promise<any> {
    return this.request('GET', `/execution/history/${sessionId}`);
  }

  async deleteHistoryBySessionId(sessionId: string): Promise<any> {
    return this.request('DELETE', `/execution/history/${sessionId}`);
  }

  async cleanupHistory(): Promise<any> {
    return this.request('POST', '/execution/history/cleanup');
  }
}
