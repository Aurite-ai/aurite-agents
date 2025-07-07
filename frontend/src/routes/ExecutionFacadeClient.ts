/**
 * Client for the Execution Facade API endpoints
 *
 * The Execution Facade provides a unified interface for running:
 * - Agents: AI-powered assistants that can use tools and maintain conversation history
 * - Simple Workflows: Sequential execution of multiple agents
 * - Custom Workflows: Python-based workflows with custom logic
 *
 * All execution happens server-side, with results returned to the client.
 */

import { BaseClient } from '../BaseClient';
import type {
  AgentRunRequest,
  AgentRunResult,
  WorkflowRunRequest,
  WorkflowExecutionResult,
  StreamEvent,
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

  /**
   * Run a simple workflow (sequential agent execution)
   *
   * Simple workflows execute a series of agents in sequence, where:
   * - Each agent receives the output of the previous agent
   * - The workflow stops if any agent fails
   * - The final output is from the last agent in the sequence
   *
   * @param workflowName - Name of the configured simple workflow
   * @param request - Request containing the initial input for the workflow
   * @returns Execution result with details about each step
   * @throws Error if the workflow is not found or execution fails
   *
   * @example
   * ```typescript
   * const result = await client.execution.runSimpleWorkflow(
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
}
