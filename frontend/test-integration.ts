/**
 * Integration test script for the Aurite API Client
 * This makes real API calls to your running backend
 *
 * Usage: npx tsx test-integration.ts
 */

import { createAuriteClient } from './src';
// Configuration - update these values as needed
const API_URL = 'http://localhost:8000';
const API_KEY = process.env.API_KEY || 'your-api-key-here';

async function runIntegrationTests() {
  console.log('🚀 Starting Aurite API Client Integration Tests');
  console.log(`📡 API URL: ${API_URL}`);
  console.log(`🔑 API Key: ${API_KEY.substring(0, 10)}...`);
  console.log('');

  const client = createAuriteClient(API_URL, API_KEY);

  try {
    // Test 1: Execution Facade Status
    console.log('1️⃣  Testing Execution Facade Status...');
    const execStatus = await client.execution.getStatus();
    console.log('✅ Execution Status:', execStatus);
    console.log('');

    // Test 2: MCP Host Status
    console.log('2️⃣  Testing MCP Host Status...');
    const hostStatus = await client.host.getStatus();
    console.log('✅ Host Status:', hostStatus);
    console.log('');

    // Test 3: List Tools
    console.log('3️⃣  Testing List Tools...');
    const tools = await client.host.listTools();
    console.log(`✅ Available Tools: ${tools.length} tools`);
    tools.forEach(tool => {
      console.log(`   - ${tool.name}: ${tool.description || 'No description'}`);
    });
    console.log('');

    // Test 3a: List Registered Servers
    console.log('3️⃣a Testing List Registered Servers...');
    const servers = await client.host.listRegisteredServers();
    console.log(`✅ Registered Servers: ${servers.length}`);
    servers.forEach(server => {
      console.log(`   - ${server.name} (${server.status})`);
    });
    console.log('');

    // Test 4: List Configurations
    console.log('4️⃣  Testing List Agent Configurations...');
    const agents = await client.config.listConfigs('agent');
    console.log(`✅ Available Agents: ${agents.length} agents`);

    // Debug: Let's see what the API actually returns
    console.log('   Raw response:', JSON.stringify(agents[0]));

    // The API should return strings, but let's handle both cases
    const agentNames: string[] = [];
    for (const agent of agents) {
      if (typeof agent === 'string') {
        agentNames.push(agent);
        console.log(`   - ${agent}`);
      } else if (agent && typeof agent === 'object') {
        // Handle object case
        const agentObj = agent as any;
        if (agentObj.name) {
          agentNames.push(agentObj.name);
          console.log(`   - ${agentObj.name}`);
        }
      }
    }
    console.log('');

    // Test 5: Run the first available agent to register its tools
    if (agentNames.length > 0) {
      const firstAgent = agentNames[0];
      console.log(`5️⃣  Testing Run Agent: ${firstAgent}...`);
      console.log('   This will register any MCP servers the agent uses');

      try {
        const result = await client.execution.runAgent(firstAgent, {
          user_message: 'Hello, please introduce yourself briefly.',
        });

        console.log('✅ Agent Response:');
        console.log(`   Status: ${result.status}`);
        console.log(`   Response: ${result.final_response?.content || 'No response'}`);
      } catch (error) {
        console.log('⚠️  Agent execution failed:', error instanceof Error ? error.message : error);
      }
      console.log('');

      // Now check tools again after running an agent
      console.log('6️⃣  Testing List Tools (after running agent)...');
      const toolsAfter = await client.host.listTools();
      console.log(`✅ Available Tools: ${toolsAfter.length} tools`);
      toolsAfter.forEach(tool => {
        console.log(`   - ${tool.name}: ${tool.description || 'No description'}`);
      });
      console.log('');

      // Test 6a: List registered servers and their tools
      console.log('6️⃣a Testing List Registered Servers and their tools (after running agent)...');
      const serversAfter = await client.host.listRegisteredServers();
      console.log(`✅ Registered Servers: ${serversAfter.length}`);
      for (const server of serversAfter) {
        console.log(`   - Server: ${server.name} (${server.status})`);
        const serverTools = await client.host.getServerTools(server.name);
        console.log(`     Tools: ${serverTools.length}`);
        serverTools.forEach(tool => {
          console.log(`       - ${tool.name}`);
        });
        // Test server status
        const serverStatus = await client.host.getServerStatus(server.name);
        console.log(`     Status: ${serverStatus.status}, Session: ${serverStatus.session_active}`);
      }
      console.log('');

      // Test 6b: Test a server
      if (serversAfter.length > 0) {
        const serverToTest = serversAfter[0].name;
        console.log(`6️⃣b Testing server: ${serverToTest}...`);
        const testResult = await client.host.testServer(serverToTest);
        console.log(`   ✅ Test result: ${testResult.status}`);
        if (testResult.error) {
          console.log(`      Error: ${testResult.error}`);
        } else {
          console.log(`      Tools discovered: ${testResult.tools_discovered?.join(', ')}`);
        }
        console.log('');
      }
    }

    // Test 7: Get Weather Agent config if it exists
    if (agentNames.includes('Weather Agent')) {
      console.log('7️⃣  Testing Get Weather Agent Configuration...');
      const weatherAgent = await client.config.getConfig('agent', 'Weather Agent');
      console.log('✅ Weather Agent Config:');
      console.log(`   - Description: ${weatherAgent.description}`);
      console.log(`   - LLM: ${weatherAgent.llm_config_id}`);
      console.log(`   - MCP Servers: ${weatherAgent.mcp_servers?.join(', ') || 'None'}`);
      console.log('');
    }

    // Test 8: Run Weather Agent specifically (if it exists)
    if (agentNames.includes('Weather Agent')) {
      console.log('8️⃣  Testing Run Weather Agent...');
      console.log('   Asking: "What is the weather in San Francisco?"');

      const result = await client.execution.runAgent('Weather Agent', {
        user_message: 'What is the weather in San Francisco?',
      });

      console.log('✅ Agent Response:');
      console.log(`   Status: ${result.status}`);
      console.log(`   Response: ${result.final_response?.content || 'No response'}`);
      console.log('');
    }

    // Test 9: Stream Agent Response (if Weather Agent exists)
    if (agentNames.includes('Weather Agent')) {
      console.log('9️⃣  Testing Stream Weather Agent...');
      console.log('   Streaming response for: "Tell me about the weather in Tokyo"');
      console.log('   Response: ');

      await client.execution.streamAgent(
        'Weather Agent',
        { user_message: 'Tell me about the weather in Tokyo' },
        event => {
          if (event.type === 'llm_response') {
            process.stdout.write(event.data.content);
          } else if (event.type === 'llm_response_stop') {
            console.log('\n');
          } else if (event.type === 'tool_call') {
            console.log(`\n   [Tool Call: ${event.data.name}]`);
          }
        }
      );
    }

    // Test 10: File Listing Operations
    console.log('🔟 Testing File Listing Operations...');
    const sources = await client.config.listConfigSources();
    console.log(`✅ Found ${sources.length} configuration sources:`);
    for (const source of sources) {
      const sourceName =
        source.project_name || (source.context === 'workspace' ? 'workspace' : 'user');
      console.log(`\n   - Source: ${sourceName} (context: ${source.context})`);
      console.log(`     Path: ${source.path}`);

      try {
        const files = await client.config.listConfigFiles(sourceName);
        console.log(`     Found ${files.length} config files:`);
        for (const file of files.slice(0, 5)) {
          console.log(`       - ${file}`);
        }
        if (files.length > 5) {
          console.log(`       ... and ${files.length - 5} more`);
        }
      } catch (e) {
        console.log(`     Could not list files for source '${sourceName}': ${e.message}`);
      }
    }
    console.log('');

    // Test 11: File-level CRUD operations
    console.log('1️⃣1️⃣ Testing File-level CRUD Operations...');
    const testFileName = 'integration_test_file.json';
    const testFileContent = JSON.stringify([{ name: 'test-component', type: 'agent' }]);
    const updatedTestFileContent = JSON.stringify([
      { name: 'updated-test-component', type: 'agent' },
    ]);

    try {
      // Create
      console.log(`   - Creating file '${testFileName}' in project_bravo...`);
      await client.config.createConfigFile('project_bravo', testFileName, testFileContent);
      console.log('   ✅ File created.');

      // Read
      console.log(`   - Reading file '${testFileName}'...`);
      const content = await client.config.getFileContent('project_bravo', testFileName);
      if (content !== testFileContent) {
        throw new Error('File content mismatch after creation!');
      }
      console.log('   ✅ File content verified.');

      // Update
      console.log(`   - Updating file '${testFileName}'...`);
      await client.config.updateConfigFile('project_bravo', testFileName, updatedTestFileContent);
      const updatedContent = await client.config.getFileContent('project_bravo', testFileName);
      if (updatedContent !== updatedTestFileContent) {
        throw new Error('File content mismatch after update!');
      }
      console.log('   ✅ File updated and verified.');
    } finally {
      // Delete
      console.log(`   - Deleting file '${testFileName}'...`);
      await client.config.deleteConfigFile('project_bravo', testFileName);
      console.log('   ✅ File deleted.');
    }
    console.log('');

    // Test 12: Component CRUD operations
    console.log('1️⃣2️⃣ Testing Component CRUD Operations...');
    const newAgentName = 'integration-test-agent';
    const newAgentConfig = {
      name: newAgentName,
      description: 'An agent created during integration tests',
      system_prompt: 'You are a test agent.',
      llm_config_id: 'my_openai_gpt4_turbo',
    };

    try {
      // Create
      console.log(`   - Creating agent '${newAgentName}'...`);
      await client.config.createConfig('agent', newAgentConfig, {
        project: 'project_bravo',
        filePath: 'integration_test_agent.json',
      });
      console.log('   ✅ Agent created.');

      // Get to verify
      console.log(`   - Getting agent '${newAgentName}' to verify creation...`);
      const createdAgent = await client.config.getConfig('agent', newAgentName);
      if (!createdAgent) {
        throw new Error('Component not found after creation!');
      }
      console.log('   ✅ Agent found after creation.');

      console.log(`   - Getting agent '${newAgentName}'...`);
      const fetchedAgent = await client.config.getConfig('agent', newAgentName);
      if (fetchedAgent.description !== newAgentConfig.description) {
        throw new Error('Component content mismatch after creation!');
      }
      console.log('   ✅ Agent content verified.');

      // Update
      console.log(`   - Updating agent '${newAgentName}'...`);
      const updatedAgentConfig = { ...newAgentConfig, description: 'An updated description' };
      await client.config.updateConfig('agent', newAgentName, updatedAgentConfig);
      const fetchedUpdatedAgent = await client.config.getConfig('agent', newAgentName);
      if (fetchedUpdatedAgent.description !== 'An updated description') {
        throw new Error('Component content mismatch after update!');
      }
      console.log('   ✅ Agent updated and verified.');
    } catch (e) {
      console.error('   ❌ ERROR in component CRUD test:', e);
      throw e; // re-throw to fail the main test
    } finally {
      // Delete
      console.log(`   - Deleting agent '${newAgentName}'...`);
      try {
        await client.config.deleteConfig('agent', newAgentName);
        console.log('   ✅ Agent deleted.');
      } catch (e) {
        console.error(`   ❌ FAILED to delete agent '${newAgentName}':`, e);
      }
    }
    console.log('');

    // Test 13: Validation
    console.log('1️⃣3️⃣ Testing Validation...');
    try {
      console.log("   - Validating 'Weather Agent'...");
      const validationResult = await client.config.validateConfig('agent', 'Weather Agent');
      console.log(`   ✅ Validation result: ${validationResult.message}`);
    } catch (e) {
      console.error("   ❌ FAILED to validate 'Weather Agent':", e);
    }

    try {
      console.log('   - Validating non-existent agent...');
      await client.config.validateConfig('agent', 'non-existent-agent');
      console.error('   ❌ FAILED: Validation of non-existent agent should have thrown an error.');
    } catch (e) {
      if (e.message.includes('not found')) {
        console.log(`   ✅ Successfully caught expected error: ${e.message}`);
      } else {
        console.error('   ❌ FAILED: Unexpected error during validation of non-existent agent:', e);
      }
    }
    console.log('');

    // Test 14: Global Validation
    console.log('1️⃣4️⃣ Testing Global Validation...');
    try {
      console.log('   - Running global validation...');
      await client.config.validateAllConfigs();
      console.log(`   ✅ Global validation passed.`);
    } catch (e) {
      console.error('   ❌ FAILED global validation:', e);
    }
    console.log('');

    // Test 15: Duplicate component creation
    console.log('1️⃣5️⃣ Testing Duplicate Component Creation...');
    try {
      console.log("   - Attempting to create duplicate agent 'Weather Agent'...");
      await client.config.createConfig('agent', {
        name: 'Weather Agent',
        description: 'A duplicate weather agent',
        system_prompt: 'You are a duplicate weather agent.',
        llm_config_id: 'my_openai_gpt4_turbo',
      });
      console.error('   ❌ FAILED: Duplicate component creation should have thrown an error.');
    } catch (e) {
      if (e.message.includes('already exists')) {
        console.log(`   ✅ Successfully caught expected error: ${e.message}`);
      } else {
        console.error('   ❌ FAILED: Unexpected error during duplicate component creation:', e);
      }
    }
    console.log('');

    console.log('✅ All integration tests completed successfully!');
  } catch (error) {
    console.error('❌ Integration test failed:', error);
    if (error instanceof Error) {
      console.error('   Error message:', error.message);
    }
    process.exit(1);
  }
}

// Run the tests
runIntegrationTests().catch(console.error);
