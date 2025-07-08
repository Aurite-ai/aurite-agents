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
        (event) => {
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
