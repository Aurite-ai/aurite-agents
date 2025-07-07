/// <reference types="jest" />
/**
 * Simple test file for the Aurite API Client
 * This demonstrates how to test the API client with mocked fetch
 */

import { createAuriteClient, AuriteApiClient } from './apiClient';

describe('AuriteApiClient', () => {
  let client: AuriteApiClient;
  const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

  beforeEach(() => {
    client = createAuriteClient('http://localhost:8000', 'test-api-key');
    mockFetch.mockClear();
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
        'http://localhost:8000/execution/agents/Weather%20Agent/run',
        {
          method: 'POST',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_message: 'What is the weather in San Francisco?',
          }),
        }
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

  describe('listTools', () => {
    it('should list available tools', async () => {
      const mockTools = [
        {
          name: 'weather_lookup',
          description: 'Look up weather information',
          inputSchema: {},
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTools,
      } as Response);

      const tools = await client.listTools();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/host/tools',
        {
          method: 'GET',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: undefined,
        }
      );

      expect(tools).toEqual(mockTools);
    });
  });

  describe('streamAgent', () => {
    it('should handle streaming responses', async () => {
      const events: any[] = [];
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

      await client.streamAgent(
        'Weather Agent',
        { user_message: 'Hello' },
        (event) => {
          events.push(event);
        }
      );

      expect(events).toHaveLength(3);
      expect(events[0].type).toBe('llm_response_start');
      expect(events[1].type).toBe('llm_response');
      expect(events[1].data.content).toBe('Hello');
      expect(events[2].type).toBe('llm_response_stop');
    });
  });
});

// Example of how to run these tests:
// npm install --save-dev jest @types/jest ts-jest
// Add to package.json scripts: "test": "jest"
// Create jest.config.js with TypeScript support
