/**
 * Integration tests for the Aurite API Client
 * These tests make real API calls to a running backend
 *
 * To run these tests:
 * 1. Ensure the Aurite API is running at http://localhost:8000
 * 2. Set the API_KEY environment variable or update the default below
 * 3. Run: npm test -- tests/integration/AuriteApiClient.integration.test.ts
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { createAuriteClient, type AuriteApiClient } from '../../src';

// Configuration - these can be overridden with environment variables
const API_URL = process.env.AURITE_API_URL || 'http://localhost:8000';
const API_KEY = process.env.API_KEY || 'test-api-key';

// Skip these tests if not explicitly enabled
const SKIP_INTEGRATION = process.env.SKIP_INTEGRATION_TESTS !== 'false';

describe.skipIf(SKIP_INTEGRATION)('Aurite API Client Integration Tests', () => {
  let client: AuriteApiClient;
  let testAgentName: string | null = null;
  let registeredServers: string[] = [];

  beforeAll(() => {
    console.log(`📡 API URL: ${API_URL}`);
    console.log(`🔑 API Key: ${API_KEY.substring(0, 10)}...`);
    client = createAuriteClient(API_URL, API_KEY);
  });

  afterAll(async () => {
    // Cleanup: Delete any test components created
    if (testAgentName) {
      try {
        await client.config.deleteConfig('agent', testAgentName);
      } catch (_e) {
        // Ignore errors during cleanup
      }
    }
  });

  describe('System Status', () => {
    it('should get execution facade status', async () => {
      const status = await client.execution.getStatus();
      expect(status).toBeDefined();
      expect(status.status).toBe('active');
    });

    it('should get MCP host status', async () => {
      const status = await client.host.getStatus();
      expect(status).toBeDefined();
      expect(status.status).toBeTruthy();
      expect(typeof status.tool_count).toBe('number');
    });
  });

  describe('MCP Host Operations', () => {
    it('should list available tools', async () => {
      const tools = await client.host.listTools();
      expect(Array.isArray(tools)).toBe(true);
      // Tools array might be empty initially
      tools.forEach(tool => {
        expect(tool.name).toBeTruthy();
      });
    });

    it('should list registered servers', async () => {
      const servers = await client.host.listRegisteredServers();
      expect(Array.isArray(servers)).toBe(true);
      registeredServers = servers.map(s => s.name);
    });

    it('should get server status for registered servers', async () => {
      for (const serverName of registeredServers) {
        const status = await client.host.getServerStatus(serverName);
        expect(status).toBeDefined();
        expect(status.name).toBe(serverName);
        expect(status.registered).toBe(true);
      }
    });

    it('should get tools for registered servers', async () => {
      for (const serverName of registeredServers) {
        const tools = await client.host.getServerTools(serverName);
        expect(Array.isArray(tools)).toBe(true);
      }
    });
  });

  describe('Configuration Management', () => {
    it('should list agent configurations', async () => {
      const agents = await client.config.listConfigs('agent');
      expect(Array.isArray(agents)).toBe(true);
      expect(agents.length).toBeGreaterThan(0);

      // Handle both string and object responses
      const agentNames: string[] = [];
      agents.forEach(agent => {
        if (typeof agent === 'string') {
          agentNames.push(agent);
          expect(typeof agent).toBe('string');
        } else if (agent && typeof agent === 'object') {
          const agentObj = agent as any;
          expect(agentObj.name).toBeTruthy();
          agentNames.push(agentObj.name);
        }
      });

      // Store for use in other tests
      registeredServers = agentNames;
    });

    it('should get a specific agent configuration', async () => {
      const agents = await client.config.listConfigs('agent');
      if (agents.length > 0) {
        // Extract agent name from either string or object
        let agentName: string;
        const firstAgent = agents[0];
        if (typeof firstAgent === 'string') {
          agentName = firstAgent;
        } else if (firstAgent && typeof firstAgent === 'object') {
          agentName = (firstAgent as any).name;
        } else {
          throw new Error('Unexpected agent format');
        }

        const config = await client.config.getConfig('agent', agentName);
        expect(config).toBeDefined();
        expect(config.name).toBe(agentName);
        expect(config.system_prompt).toBeTruthy();
      }
    });

    it('should list configuration sources', async () => {
      const sources = await client.config.listConfigSources();
      expect(Array.isArray(sources)).toBe(true);
      expect(sources.length).toBeGreaterThan(0);

      sources.forEach(source => {
        expect(source.context).toMatch(/^(user|workspace|project)$/);
        expect(source.path).toBeTruthy();
      });
    });

    it('should list configuration files for sources', async () => {
      const sources = await client.config.listConfigSources();
      for (const source of sources.slice(0, 2)) {
        // Test first 2 sources
        const sourceName =
          source.project_name || (source.context === 'workspace' ? 'workspace' : 'user');

        try {
          const files = await client.config.listConfigFiles(sourceName);
          expect(Array.isArray(files)).toBe(true);
        } catch (e) {
          // Some sources might not be accessible, which is okay
          expect(e.message).toContain('not found');
        }
      }
    });
  });

  describe('Component CRUD Operations', () => {
    const testAgentConfig = {
      name: 'integration-test-agent',
      description: 'An agent created during integration tests',
      system_prompt: 'You are a test agent.',
      llm_config_id: 'my_openai_gpt4_turbo',
    };

    it('should create a new agent', async () => {
      testAgentName = testAgentConfig.name;

      await client.config.createConfig('agent', testAgentConfig, {
        project: 'project_bravo',
        filePath: 'integration_test_agent.json',
      });

      // Verify creation
      const created = await client.config.getConfig('agent', testAgentName);
      expect(created).toBeDefined();
      expect(created.name).toBe(testAgentName);
      expect(created.description).toBe(testAgentConfig.description);
    });

    it('should update the agent', async () => {
      if (!testAgentName) {
        throw new Error('Test agent not created');
      }

      const updatedConfig = {
        ...testAgentConfig,
        description: 'An updated description',
      };

      await client.config.updateConfig('agent', testAgentName, updatedConfig);

      // Verify update
      const updated = await client.config.getConfig('agent', testAgentName);
      expect(updated.description).toBe('An updated description');
    });

    it('should validate the agent configuration', async () => {
      if (!testAgentName) {
        throw new Error('Test agent not created');
      }

      const result = await client.config.validateConfig('agent', testAgentName);
      expect(result).toBeDefined();
      expect(result.message).toContain('valid');
    });

    it('should delete the agent', async () => {
      if (!testAgentName) {
        throw new Error('Test agent not created');
      }

      await client.config.deleteConfig('agent', testAgentName);

      // Verify deletion
      await expect(client.config.getConfig('agent', testAgentName)).rejects.toThrow();

      testAgentName = null; // Clear so afterAll doesn't try to delete again
    });

    it('should prevent duplicate component creation', async () => {
      const agents = await client.config.listConfigs('agent');
      if (agents.length > 0) {
        // Extract agent name from either string or object
        let existingAgentName: string;
        const firstAgent = agents[0];
        if (typeof firstAgent === 'string') {
          existingAgentName = firstAgent;
        } else if (firstAgent && typeof firstAgent === 'object') {
          existingAgentName = (firstAgent as any).name;
        } else {
          throw new Error('Unexpected agent format');
        }

        await expect(
          client.config.createConfig('agent', {
            name: existingAgentName,
            description: 'A duplicate agent',
            system_prompt: 'Duplicate',
            llm_config_id: 'my_openai_gpt4_turbo',
          })
        ).rejects.toThrow(/already exists/);
      }
    });
  });

  describe('File Operations', () => {
    const testFileName = 'integration_test_file.json';
    const testContent = JSON.stringify([{ name: 'test-component', type: 'agent' }], null, 2);
    const updatedContent = JSON.stringify([{ name: 'updated-component', type: 'agent' }], null, 2);

    it('should create a config file', async () => {
      await client.config.createConfigFile('project_bravo', testFileName, testContent);

      // Verify creation
      const content = await client.config.getFileContent('project_bravo', testFileName);
      expect(content).toBe(testContent);
    });

    it('should update the config file', async () => {
      await client.config.updateConfigFile('project_bravo', testFileName, updatedContent);

      // Verify update
      const content = await client.config.getFileContent('project_bravo', testFileName);
      expect(content).toBe(updatedContent);
    });

    it('should delete the config file', async () => {
      await client.config.deleteConfigFile('project_bravo', testFileName);

      // Verify deletion
      await expect(client.config.getFileContent('project_bravo', testFileName)).rejects.toThrow();
    });
  });

  describe('Agent Execution', () => {
    it('should run an agent', async () => {
      const agents = await client.config.listConfigs('agent');
      if (agents.length > 0) {
        // Extract agent name from either string or object
        let agentName: string;
        const firstAgent = agents[0];
        if (typeof firstAgent === 'string') {
          agentName = firstAgent;
        } else if (firstAgent && typeof firstAgent === 'object') {
          agentName = (firstAgent as any).name;
        } else {
          throw new Error('Unexpected agent format');
        }

        const result = await client.execution.runAgent(agentName, {
          user_message: 'Hello, please introduce yourself briefly.',
        });

        expect(result).toBeDefined();
        expect(result.status).toBeTruthy();
        expect(result.final_response).toBeDefined();
        expect(result.final_response?.content).toBeTruthy();
      }
    });

    it('should handle agent not found error', async () => {
      await expect(
        client.execution.runAgent('non-existent-agent', {
          user_message: 'Hello',
        })
      ).rejects.toThrow();
    });
  });

  describe('Project and Workspace Management', () => {
    const testProjectName = `test-project-${Date.now()}`;

    it('should list workspaces', async () => {
      const workspaces = await client.config.listWorkspaces();
      expect(Array.isArray(workspaces)).toBe(true);
      expect(workspaces.length).toBeGreaterThan(0);
      expect(workspaces[0].name).toBeTruthy();
    });

    it('should get the active workspace', async () => {
      const workspace = await client.config.getActiveWorkspace();
      expect(workspace).toBeDefined();
      expect(workspace?.is_active).toBe(true);
    });

    it('should list projects', async () => {
      const projects = await client.config.listProjects();
      expect(Array.isArray(projects)).toBe(true);
    });

    it('should create a new project', async () => {
      const response = await client.config.createProject(testProjectName, 'A test project');
      expect(response.message).toContain('created successfully');

      const projects = await client.config.listProjects();
      const newProject = projects.find(p => p.name === testProjectName);
      expect(newProject).toBeDefined();
    });

    it('should get the new project', async () => {
      const project = await client.config.getProject(testProjectName);
      expect(project).toBeDefined();
      expect(project.name).toBe(testProjectName);
      expect(project.description).toBe('A test project');
    });

    it('should update the project', async () => {
      const updates = { description: 'Updated description' };
      await client.config.updateProject(testProjectName, updates);

      const updatedProject = await client.config.getProject(testProjectName);
      expect(updatedProject.description).toBe('Updated description');
    });

    it('should delete the project', async () => {
      await client.config.deleteProject(testProjectName);

      await expect(client.config.getProject(testProjectName)).rejects.toThrow(/not found/);
    });

    it('should get the active project', async () => {
      const project = await client.config.getActiveProject();
      // This can be null if not running inside a project context, which is fine
      if (project) {
        expect(project.is_active).toBe(true);
      }
    });
  });

  describe('History', () => {
    it('should get agent history', async () => {
      const agents = await client.config.listConfigs('agent');
      if (agents.length > 0) {
        const agentName = typeof agents[0] === 'string' ? agents[0] : (agents[0] as any).name;
        const history = await client.execution.getAgentHistory(agentName);
        expect(Array.isArray(history.sessions)).toBe(true);
      }
    });
  });

  describe('System', () => {
    it('should get system info', async () => {
      const info = await client.system.getSystemInfo();
      expect(info).toBeDefined();
      expect(info.platform).toBeTruthy();
    });

    it('should get framework version', async () => {
      const version = await client.system.getFrameworkVersion();
      expect(version).toBeDefined();
      expect(version.version).toBeTruthy();
    });

    it('should get system capabilities', async () => {
      const capabilities = await client.system.getSystemCapabilities();
      expect(capabilities).toBeDefined();
      expect(capabilities.mcp_support).toBe(true);
    });
  });

  describe('Validation', () => {
    it('should validate all configurations', async () => {
      // This might throw if there are invalid configs, which is okay for the test
      try {
        await client.config.validateAllConfigs();
      } catch (e) {
        // If validation fails, ensure it's a proper error
        expect(e).toBeInstanceOf(Error);
        expect(e.message).toBeTruthy();
      }
    });

    it('should handle validation of non-existent component', async () => {
      await expect(client.config.validateConfig('agent', 'non-existent-agent')).rejects.toThrow(
        /not found/
      );
    });
  });
});

// Note about running these tests
console.log(`
📝 Integration Test Notes:
- These tests require a running Aurite API at ${API_URL}
- Set SKIP_INTEGRATION_TESTS=false to run these tests
- Set AURITE_API_URL and API_KEY environment variables to override defaults
- Example: SKIP_INTEGRATION_TESTS=false npm test -- tests/integration/
`);
