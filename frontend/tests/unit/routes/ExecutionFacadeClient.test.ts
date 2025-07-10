/**
 * Tests for ExecutionFacadeClient
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ExecutionFacadeClient } from '../../../src/routes/ExecutionFacadeClient';
import type { ApiConfig, StreamEvent } from '../../../src/types';

describe('ExecutionFacadeClient', () => {
  let client: ExecutionFacadeClient;
  const mockFetch = vi.fn();
  const config: ApiConfig = {
    baseUrl: process.env.AURITE_API_BASE_URL || 'http://localhost:8000',
    apiKey: process.env.AURITE_API_KEY || 'test-api-key',
  };

  beforeEach(() => {
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
  });
});
