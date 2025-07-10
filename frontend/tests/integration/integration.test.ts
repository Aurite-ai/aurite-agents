/**
 * Integration tests for the Aurite API Client
 * These tests make real API calls to a running backend server
 *
 * To run: npm test -- tests/integration/integration.test.ts
 *
 * Prerequisites:
 * - Aurite server running on localhost:8000
 * - Valid API key (set via API_KEY environment variable)
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { createAuriteClient, AuriteApiClient } from '../../src';

// Configuration
const API_URL = process.env.AURITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = process.env.AURITE_API_KEY || 'your_test_key';

describe('Aurite API Client Integration Tests', () => {
  let client: AuriteApiClient;

  beforeAll(() => {
    client = createAuriteClient(API_URL, API_KEY);
  });

  describe('Execution Facade', () => {
    it('should get execution status', async () => {
      const status = await client.execution.getStatus();
      expect(status).toHaveProperty('status');
      expect(status.status).toBe('active');
    });
  });

  describe('MCP Host', () => {
    it('should get host status', async () => {
      const status = await client.host.getStatus();
      expect(status).toHaveProperty('status');
      expect(status.status).toBe('active');
      expect(status).toHaveProperty('tool_count');
      expect(typeof status.tool_count).toBe('number');
    });

    it('should list available tools', async () => {
      const tools = await client.host.listTools();
      expect(Array.isArray(tools)).toBe(true);

      // Tools might be empty initially, but after running an agent they should be available
      tools.forEach(tool => {
        expect(tool).toHaveProperty('name');
        expect(typeof tool.name).toBe('string');
      });
    });
  });

  describe('Configuration Manager', () => {
    it('should list agent configurations', async () => {
      const agents = await client.config.listConfigs('agent');
      expect(Array.isArray(agents)).toBe(true);
      expect(agents.length).toBeGreaterThan(0);

      // Check if we have the expected Weather Agent
      const agentNames = agents.map(agent =>
        typeof agent === 'string' ? agent : (agent as any).name
      );
      expect(agentNames).toContain('Weather Agent');
    });

    it('should get specific agent configuration', async () => {
      const weatherAgent = await client.config.getConfig('agent', 'Weather Agent');
      expect(weatherAgent).toHaveProperty('name');
      expect(weatherAgent.name).toBe('Weather Agent');
      expect(weatherAgent).toHaveProperty('description');
      expect(weatherAgent).toHaveProperty('llm_config_id');
      expect(weatherAgent).toHaveProperty('mcp_servers');
      expect(Array.isArray(weatherAgent.mcp_servers)).toBe(true);
    });
  });

  describe('Agent Execution', () => {
    it('should run an agent successfully', async () => {
      const result = await client.execution.runAgent('Weather Agent', {
        user_message: 'Hello, please introduce yourself briefly.',
      });

      expect(result).toHaveProperty('status');
      expect(result.status).toBe('success');
      expect(result).toHaveProperty('final_response');
      expect(result.final_response).toBeDefined();
      expect(result.final_response!).toHaveProperty('content');
      expect(typeof result.final_response!.content).toBe('string');
    });

    it('should run weather agent with weather query', async () => {
      const result = await client.execution.runAgent('Weather Agent', {
        user_message: 'What is the weather in San Francisco?',
      });

      expect(result).toHaveProperty('status');
      expect(result.status).toBe('success');
      expect(result).toHaveProperty('final_response');
      expect(result.final_response).toBeDefined();
      expect(result.final_response!).toHaveProperty('content');

      const response = result.final_response!.content;
      expect(typeof response).toBe('string');
      expect(response.toLowerCase()).toContain('san francisco');
    });

    it('should stream agent responses', async () => {
      const events: any[] = [];

      await client.execution.streamAgent(
        'Weather Agent',
        { user_message: 'Tell me about the weather in Tokyo' },
        event => {
          events.push(event);
        }
      );

      expect(events.length).toBeGreaterThan(0);

      // Should have at least response start and stop events
      const eventTypes = events.map(e => e.type);
      expect(eventTypes).toContain('llm_response_start');
      expect(eventTypes).toContain('llm_response_stop');

      // Should have some actual response content
      const responseEvents = events.filter(e => e.type === 'llm_response');
      expect(responseEvents.length).toBeGreaterThan(0);
    });
  });

  describe('Tool Registration', () => {
    it('should register tools after running an agent', async () => {
      // First, run an agent to register its MCP servers
      await client.execution.runAgent('Weather Agent', {
        user_message: 'Hello',
      });

      // Now check that tools are available
      const tools = await client.host.listTools();
      expect(tools.length).toBeGreaterThan(0);

      // Should have weather-related tools
      const toolNames = tools.map(t => t.name);
      expect(toolNames).toContain('weather_lookup');
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid agent name', async () => {
      await expect(
        client.execution.runAgent('NonExistent Agent', {
          user_message: 'Hello',
        })
      ).rejects.toThrow();
    });

    it('should handle invalid config type', async () => {
      // The API returns an empty array for invalid config types rather than throwing an error
      const result = await client.config.listConfigs('invalid_type');
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBe(0);
    });

    it('should handle non-existent configuration', async () => {
      await expect(client.config.getConfig('agent', 'NonExistent Agent')).rejects.toThrow();
    });
  });
});
