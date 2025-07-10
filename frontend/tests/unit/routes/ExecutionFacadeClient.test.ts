/**
 * Tests for ExecutionFacadeClient
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ExecutionFacadeClient } from '../../../src/routes/ExecutionFacadeClient';
import { getApiClientConfig } from '../../../src/config/environment';
import type { ApiConfig, StreamEvent } from '../../../src/types';

describe('ExecutionFacadeClient', () => {
  let client: ExecutionFacadeClient;
  const mockFetch = vi.fn();
  let config: ApiConfig;

  beforeEach(() => {
    // Get config from environment with test overrides
    config = getApiClientConfig({
      baseUrl: 'http://localhost:8000',
      apiKey: 'test-api-key',
    });

    client = new ExecutionFacadeClient(config);
    mockFetch.mockClear();
    (globalThis as any).fetch = mockFetch;
  });

  describe('getStatus', () => {
    it('should get execution facade status', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'active' }),
      } as Response);

      const result = await client.getStatus();

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/execution/status`,
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual({ status: 'active' });
    });

    it('should handle status check errors', async () => {
      const errorResponse = {
        ok: false,
        status: 503,
        json: async () => ({ detail: 'Service unavailable' }),
      } as Response;

      // Mock all retry attempts
      mockFetch.mockResolvedValue(errorResponse);

      await expect(client.getStatus()).rejects.toThrow('Service unavailable');
    });
  });

  describe('runAgent', () => {
    it('should successfully run an agent', async () => {
      const mockResponse = {
        status: 'success',
        final_response: {
          role: 'assistant',
          content: 'The weather in San Francisco is sunny and 72°F.',
        },
        conversation_history: [],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await client.runAgent('Weather Agent', {
        user_message: 'What is the weather in San Francisco?',
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/execution/agents/Weather%20Agent/run`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_message: 'What is the weather in San Francisco?',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle API errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Agent not found' }),
      } as Response);

      await expect(
        client.runAgent('NonExistentAgent', {
          user_message: 'Hello',
        })
      ).rejects.toThrow('Agent not found');
    });

    it('should run agent with session ID', async () => {
      const mockResponse = {
        status: 'success',
        final_response: {
          role: 'assistant',
          content: 'I remember our previous conversation.',
        },
        conversation_history: [
          { role: 'user', content: 'Previous message' },
          { role: 'assistant', content: 'Previous response' },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await client.runAgent('Memory Agent', {
        user_message: 'Do you remember me?',
        session_id: 'user-123',
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/execution/agents/Memory%20Agent/run`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_message: 'Do you remember me?',
            session_id: 'user-123',
          }),
        })
      );

      expect(result.conversation_history).toHaveLength(2);
    });
  });

  describe('streamAgent', () => {
    it('should handle streaming responses', async () => {
      const events: StreamEvent[] = [];
      const mockStream = new ReadableStream({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode('data: {"type":"llm_response_start","data":{}}\n\n')
          );
          controller.enqueue(
            new TextEncoder().encode('data: {"type":"llm_response","data":{"content":"Hello"}}\n\n')
          );
          controller.enqueue(
            new TextEncoder().encode('data: {"type":"llm_response_stop","data":{}}\n\n')
          );
          controller.close();
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockStream,
      } as Response);

      await client.streamAgent('Weather Agent', { user_message: 'Hello' }, event => {
        events.push(event);
      });

      expect(events).toHaveLength(3);
      expect(events[0].type).toBe('llm_response_start');
      expect(events[1].type).toBe('llm_response');
      expect(events[1].data.content).toBe('Hello');
      expect(events[2].type).toBe('llm_response_stop');
    });

    it('should handle stream errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      } as Response);

      await expect(
        client.streamAgent('Weather Agent', { user_message: 'Hello' }, () => {})
      ).rejects.toThrow('Stream request failed: 500');
    });

    it('should handle tool call events in stream', async () => {
      const events: StreamEvent[] = [];
      const mockStream = new ReadableStream({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode(
              'data: {"type":"tool_call","data":{"name":"weather_lookup","args":{"location":"SF"}}}\n\n'
            )
          );
          controller.enqueue(
            new TextEncoder().encode(
              'data: {"type":"tool_result","data":{"result":"Sunny, 72°F"}}\n\n'
            )
          );
          controller.close();
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockStream,
      } as Response);

      await client.streamAgent('Weather Agent', { user_message: 'Weather?' }, event => {
        events.push(event);
      });

      expect(events).toHaveLength(2);
      expect(events[0].type).toBe('tool_call');
      expect(events[0].data.name).toBe('weather_lookup');
      expect(events[1].type).toBe('tool_result');
    });
  });

  describe('runSimpleWorkflow', () => {
    it('should run a simple workflow', async () => {
      const mockResponse = {
        status: 'success',
        steps: [
          { step_name: 'weather_check', status: 'success', result: {} },
          { step_name: 'outfit_suggestion', status: 'success', result: {} },
        ],
        final_output: 'Wear a light jacket',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await client.runSimpleWorkflow('Weather Planning Workflow', {
        initial_input: 'What should I wear today?',
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/execution/workflows/simple/Weather%20Planning%20Workflow/run`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            initial_input: 'What should I wear today?',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle workflow failures', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Workflow not found' }),
      } as Response);

      await expect(
        client.runSimpleWorkflow('NonExistentWorkflow', { initial_input: 'test' })
      ).rejects.toThrow('Workflow not found');
    });

    it('should handle workflow step failures', async () => {
      const mockResponse = {
        status: 'failed',
        steps: [
          { step_name: 'step1', status: 'success', result: {} },
          { step_name: 'step2', status: 'failed', error: 'Tool not available' },
        ],
        error: 'Workflow failed at step: step2',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await client.runSimpleWorkflow('Failing Workflow', {
        initial_input: 'test',
      });

      expect(result.status).toBe('failed');
      expect(result.steps[1].status).toBe('failed');
    });
  });

  describe('runCustomWorkflow', () => {
    it('should run a custom workflow', async () => {
      const mockResponse = {
        result: 'Custom workflow completed',
        data: { processed: true },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await client.runCustomWorkflow('DataProcessingWorkflow', {
        initial_input: { data: [1, 2, 3] },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/execution/workflows/custom/DataProcessingWorkflow/run`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            initial_input: { data: [1, 2, 3] },
          }),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle custom workflow errors', async () => {
      const errorResponse = {
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Workflow execution failed: Invalid input data' }),
      } as Response;

      // Mock all retry attempts
      mockFetch.mockResolvedValue(errorResponse);

      await expect(
        client.runCustomWorkflow('DataProcessingWorkflow', { initial_input: null })
      ).rejects.toThrow('Workflow execution failed: Invalid input data');
    });

    it('should handle complex custom workflow results', async () => {
      const mockResponse = {
        summary: {
          total_processed: 100,
          successful: 95,
          failed: 5,
        },
        details: [
          { id: 1, status: 'success' },
          { id: 2, status: 'failed', error: 'Invalid format' },
        ],
        metadata: {
          execution_time: 1.23,
          workflow_version: '1.0.0',
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await client.runCustomWorkflow('ComplexWorkflow', {
        initial_input: { batch_size: 100 },
      });

      expect(result.summary.total_processed).toBe(100);
      expect(result.metadata.workflow_version).toBe('1.0.0');
    });
  });
});
