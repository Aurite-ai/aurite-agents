/**
 * Example usage of the Aurite API Client
 */

import type { StreamEvent } from './src';
import { createAuriteClient } from './src/AuriteApiClient';

// Initialize the client
const client = createAuriteClient('http://localhost:8000', 'your-api-key-here');

// Example 1: Run an agent and get the result
async function runWeatherAgent() {
  try {
    const result = await client.execution.runAgent('Weather Agent', {
      user_message: 'What is the weather in San Francisco?',
    });

    console.log('Agent Status:', result.status);
    console.log('Response:', result.final_response?.content);
  } catch (error) {
    console.error('Error running agent:', error);
  }
}

// Example 2: Stream agent responses
async function streamWeatherAgent() {
  try {
    await client.execution.streamAgent(
      'Weather Agent',
      {
        user_message: 'What is the weather in Tokyo?',
      },
      (event: StreamEvent) => {
        switch (event.type) {
          case 'llm_response_start':
            console.log('Agent started responding...');
            break;
          case 'llm_response':
            console.log(event.data.content);
            break;
          case 'llm_response_stop':
            console.log('\nAgent finished responding.');
            break;
          case 'tool_call':
            console.log('\nCalling tool:', event.data.name);
            break;
          case 'tool_output':
            console.log('Tool output:', event.data.output);
            break;
          case 'error':
            console.error('Error:', event.data.message);
            break;
        }
      }
    );
  } catch (error) {
    console.error('Error streaming agent:', error);
  }
}

// Example 3: Run a workflow
async function runWeatherWorkflow() {
  try {
    const result = await client.execution.runSimpleWorkflow('Weather Planning Workflow', {
      initial_input: 'What should I wear in London today?',
    });

    console.log('Workflow Status:', result.status);
    result.steps.forEach((step) => {
      console.log(`Step ${step.step_name}: ${step.status}`);
    });
  } catch (error) {
    console.error('Error running workflow:', error);
  }
}

// Example 4: Work with MCP tools directly
async function useToolsDirectly() {
  try {
    // List available tools
    const tools = await client.host.listTools();
    console.log('Available tools:', tools.map(t => t.name));

    // Register a server if needed
    await client.host.registerServerByName('weather_server');

    // Call a tool
    const weatherResult = await client.host.callTool('weather_lookup', {
      location: 'New York',
    });
    console.log('Weather data:', weatherResult);

    // Unregister when done
    await client.host.unregisterServer('weather_server');
  } catch (error) {
    console.error('Error working with tools:', error);
  }
}

// Example 5: Manage configurations
async function manageConfigs() {
  try {
    // List all agents
    const agents = await client.config.listConfigs('agent');
    console.log('Available agents:', agents);

    // Get specific agent config
    const weatherAgent = await client.config.getConfig('agent', 'Weather Agent');
    console.log('Weather Agent config:', weatherAgent);

    // Create a new agent
    await client.config.createConfig('agent', {
      name: 'My Custom Agent',
      description: 'A custom agent for testing',
      system_prompt: 'You are a helpful assistant.',
      llm_config_id: 'anthropic_claude_3_haiku',
      mcp_servers: ['weather_server'],
    });

    // Update the agent
    await client.config.updateConfig('agent', 'My Custom Agent', {
      name: 'My Custom Agent',
      description: 'Updated description',
      system_prompt: 'You are a very helpful assistant.',
      llm_config_id: 'anthropic_claude_3_haiku',
      mcp_servers: ['weather_server'],
    });

    // Delete the agent
    await client.config.deleteConfig('agent', 'My Custom Agent');
  } catch (error) {
    console.error('Error managing configs:', error);
  }
}

// Run examples
async function main() {
  console.log('=== Running Weather Agent ===');
  await runWeatherAgent();

  console.log('\n=== Streaming Weather Agent ===');
  await streamWeatherAgent();

  console.log('\n=== Running Weather Workflow ===');
  await runWeatherWorkflow();

  console.log('\n=== Using Tools Directly ===');
  await useToolsDirectly();

  console.log('\n=== Managing Configurations ===');
  await manageConfigs();
}

// Uncomment to run examples
main().catch(console.error);
