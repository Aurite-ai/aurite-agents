/**
 * Configuration Listing Example
 *
 * This example demonstrates how to list and retrieve configurations:
 * - List all configuration types
 * - Get specific configurations
 * - Explore configuration structures
 * - Compare different configuration types
 */

import { createExampleClient, runExample, handleExampleError } from '../shared/client-setup';

async function listAllConfigTypes() {
  const client = await createExampleClient();

  console.log('\n📋 Example 1: List All Configuration Types');

  const configTypes = ['agent', 'llm', 'mcp_server', 'linear_workflow', 'custom_workflow'];

  for (const configType of configTypes) {
    try {
      console.log(`\n🔍 Listing ${configType} configurations...`);
      const configs = await client.config.listConfigs(configType);

      console.log(`✅ Found ${configs.length} ${configType} configurations:`);
      configs.forEach((config: any, index: number) => {
        console.log(`   ${index + 1}. ${config.name}`);
      });
    } catch (error) {
      console.log(`❌ Failed to list ${configType} configurations:`);
      handleExampleError(error, `List ${configType}`);
    }
  }
}

async function exploreAgentConfigurations() {
  const client = await createExampleClient();

  console.log('\n📋 Example 2: Explore Agent Configurations');

  try {
    // List all agents
    const agents = await client.config.listConfigs('agent');
    console.log(`✅ Found ${agents.length} agent configurations`);

    // Get details for each agent
    for (const agent of agents.slice(0, 3)) {
      // Limit to first 3 for brevity
      try {
        console.log(`\n🤖 Agent: ${agent.name}`);
        const agentConfig = await client.config.getConfig('agent', agent.name);

        console.log('   Configuration Details:');
        console.log(`   - Description: ${agentConfig.description || 'No description'}`);
        console.log(`   - LLM Config: ${agentConfig.llm_config_id || 'Not specified'}`);
        console.log(`   - MCP Servers: ${agentConfig.mcp_servers?.join(', ') || 'None'}`);
        console.log(`   - Max Iterations: ${agentConfig.max_iterations || 'Default'}`);
        console.log(`   - Include History: ${agentConfig.include_history || false}`);

        if (agentConfig.system_prompt) {
          const prompt = agentConfig.system_prompt.substring(0, 100);
          console.log(
            `   - System Prompt: ${prompt}${prompt.length < agentConfig.system_prompt.length ? '...' : ''}`
          );
        }
      } catch (error) {
        console.log(`   ❌ Failed to get details for ${agent.name}`);
        handleExampleError(error, `Get Agent ${agent.name}`);
      }
    }
  } catch (error) {
    handleExampleError(error, 'Explore Agents');
  }
}

async function exploreLLMConfigurations() {
  const client = await createExampleClient();

  console.log('\n📋 Example 3: Explore LLM Configurations');

  try {
    // List all LLM configurations
    const llms = await client.config.listConfigs('llm');
    console.log(`✅ Found ${llms.length} LLM configurations`);

    // Get details for each LLM config
    for (const llm of llms.slice(0, 3)) {
      // Limit to first 3
      try {
        console.log(`\n🧠 LLM Config: ${llm.name}`);
        const llmConfig = await client.config.getConfig('llm', llm.name);

        console.log('   Configuration Details:');
        console.log(`   - Provider: ${llmConfig.provider || 'Not specified'}`);
        console.log(`   - Model: ${llmConfig.model || 'Not specified'}`);
        console.log(`   - Temperature: ${llmConfig.temperature ?? 'Default'}`);
        console.log(`   - Max Tokens: ${llmConfig.max_tokens || 'Default'}`);

        if (llmConfig.api_key_env_var) {
          console.log(`   - API Key Env Var: ${llmConfig.api_key_env_var}`);
        }
      } catch (error) {
        console.log(`   ❌ Failed to get details for ${llm.name}`);
        handleExampleError(error, `Get LLM ${llm.name}`);
      }
    }
  } catch (error) {
    handleExampleError(error, 'Explore LLMs');
  }
}

async function exploreMCPServerConfigurations() {
  const client = await createExampleClient();

  console.log('\n📋 Example 4: Explore MCP Server Configurations');

  try {
    // List all MCP server configurations
    const servers = await client.config.listConfigs('mcp_server');
    console.log(`✅ Found ${servers.length} MCP server configurations`);

    // Get details for each server
    for (const server of servers.slice(0, 3)) {
      // Limit to first 3
      try {
        console.log(`\n🔧 MCP Server: ${server.name}`);
        const serverConfig = await client.config.getConfig('mcp_server', server.name);

        console.log('   Configuration Details:');
        console.log(`   - Transport Type: ${serverConfig.transport_type || 'Not specified'}`);
        console.log(`   - Server Path: ${serverConfig.server_path || 'Not specified'}`);
        console.log(`   - Capabilities: ${serverConfig.capabilities?.join(', ') || 'None'}`);
        console.log(`   - Timeout: ${serverConfig.timeout || 'Default'}`);

        if (serverConfig.description) {
          console.log(`   - Description: ${serverConfig.description}`);
        }

        if (serverConfig.http_endpoint) {
          console.log(`   - HTTP Endpoint: ${serverConfig.http_endpoint}`);
        }
      } catch (error) {
        console.log(`   ❌ Failed to get details for ${server.name}`);
        handleExampleError(error, `Get Server ${server.name}`);
      }
    }
  } catch (error) {
    handleExampleError(error, 'Explore MCP Servers');
  }
}

async function exploreWorkflowConfigurations() {
  const client = await createExampleClient();

  console.log('\n📋 Example 5: Explore Workflow Configurations');

  try {
    // Check linear workflows
    console.log('\n🔄 Linear Workflows:');
    const linearWorkflows = await client.config.listConfigs('linear_workflow');
    console.log(`   Found ${linearWorkflows.length} linear workflow configurations`);

    for (const workflow of linearWorkflows.slice(0, 2)) {
      try {
        const workflowConfig = await client.config.getConfig('linear_workflow', workflow.name);
        console.log(`\n   📋 Linear Workflow: ${workflow.name}`);
        console.log(`      Description: ${workflowConfig.description || 'No description'}`);
        console.log(`      Steps: ${workflowConfig.steps?.length || 0} agents`);

        if (workflowConfig.steps) {
          workflowConfig.steps.forEach((step: any, index: number) => {
            console.log(`         ${index + 1}. ${step.agent_name || step}`);
          });
        }
      } catch (error) {
        console.log(`   ❌ Failed to get linear workflow ${workflow.name}`);
        handleExampleError(error, `Get Linear Workflow ${workflow.name}`);
      }
    }

    // Check custom workflows
    console.log('\n🔄 Custom Workflows:');
    const customWorkflows = await client.config.listConfigs('custom_workflow');
    console.log(`   Found ${customWorkflows.length} custom workflow configurations`);

    for (const workflow of customWorkflows.slice(0, 2)) {
      try {
        const workflowConfig = await client.config.getConfig('custom_workflow', workflow.name);
        console.log(`\n   🐍 Custom Workflow: ${workflow.name}`);
        console.log(`      Description: ${workflowConfig.description || 'No description'}`);
        console.log(`      Class Name: ${workflowConfig.class_name || 'Not specified'}`);
        console.log(`      Module Path: ${workflowConfig.module_path || 'Not specified'}`);
      } catch (error) {
        console.log(`   ❌ Failed to get custom workflow ${workflow.name}`);
        handleExampleError(error, `Get Custom Workflow ${workflow.name}`);
      }
    }
  } catch (error) {
    handleExampleError(error, 'Explore Workflows');
  }
}

async function configurationSummary() {
  const client = await createExampleClient();

  console.log('\n📋 Example 6: Configuration Summary');

  const configTypes = ['agent', 'llm', 'mcp_server', 'linear_workflow', 'custom_workflow'];
  const summary: Record<string, number> = {};

  try {
    for (const configType of configTypes) {
      try {
        const configs = await client.config.listConfigs(configType);
        summary[configType] = configs.length;
      } catch (error) {
        summary[configType] = 0;
        console.log(`⚠️  Could not count ${configType} configurations`);
      }
    }

    console.log('\n📊 Configuration Summary:');
    console.log('='.repeat(40));
    Object.entries(summary).forEach(([type, count]) => {
      const displayType = type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
      console.log(`   ${displayType.padEnd(20)}: ${count}`);
    });
    console.log('='.repeat(40));

    const total = Object.values(summary).reduce((a, b) => a + b, 0);
    console.log(`   ${'Total Configurations'.padEnd(20)}: ${total}`);
  } catch (error) {
    handleExampleError(error, 'Configuration Summary');
  }
}

async function searchConfigurations() {
  const client = await createExampleClient();

  console.log('\n📋 Example 7: Search Configurations');

  try {
    // Search for weather-related configurations
    const searchTerm = 'weather';
    console.log(`🔍 Searching for configurations containing "${searchTerm}"...`);

    const configTypes = ['agent', 'llm', 'mcp_server', 'linear_workflow'];
    let foundConfigs = 0;

    for (const configType of configTypes) {
      try {
        const configs = await client.config.listConfigs(configType);
        const matchingConfigs = configs.filter((config: any) =>
          config.name.toLowerCase().includes(searchTerm.toLowerCase())
        );

        if (matchingConfigs.length > 0) {
          console.log(`\n✅ Found ${matchingConfigs.length} ${configType} configurations:`);
          matchingConfigs.forEach((config: any) => {
            console.log(`   - ${config.name}`);
            foundConfigs++;
          });
        }
      } catch (error) {
        console.log(`❌ Could not search ${configType} configurations`);
      }
    }

    if (foundConfigs === 0) {
      console.log(`❌ No configurations found containing "${searchTerm}"`);
    } else {
      console.log(`\n✅ Total configurations found: ${foundConfigs}`);
    }
  } catch (error) {
    handleExampleError(error, 'Search Configurations');
  }
}

async function configurationErrorHandling() {
  const client = await createExampleClient();

  console.log('\n📋 Example 8: Configuration Error Handling');

  // Test 1: Invalid configuration type
  try {
    await client.config.listConfigs('invalid_type');
  } catch (error) {
    console.log('✅ Expected error for invalid config type:');
    handleExampleError(error, 'Invalid Config Type');
  }

  // Test 2: Non-existent configuration
  try {
    await client.config.getConfig('agent', 'Non-Existent Agent');
  } catch (error) {
    console.log('\n✅ Expected error for non-existent config:');
    handleExampleError(error, 'Non-existent Config');
  }

  // Test 3: Empty configuration name
  try {
    await client.config.getConfig('agent', '');
  } catch (error) {
    console.log('\n✅ Expected error for empty config name:');
    handleExampleError(error, 'Empty Config Name');
  }
}

// Main execution
async function main() {
  await runExample('List All Config Types', listAllConfigTypes);
  await runExample('Explore Agent Configurations', exploreAgentConfigurations);
  await runExample('Explore LLM Configurations', exploreLLMConfigurations);
  await runExample('Explore MCP Server Configurations', exploreMCPServerConfigurations);
  await runExample('Explore Workflow Configurations', exploreWorkflowConfigurations);
  await runExample('Configuration Summary', configurationSummary);
  await runExample('Search Configurations', searchConfigurations);
  await runExample('Configuration Error Handling', configurationErrorHandling);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export {
  listAllConfigTypes,
  exploreAgentConfigurations,
  exploreLLMConfigurations,
  exploreMCPServerConfigurations,
  exploreWorkflowConfigurations,
  configurationSummary,
  searchConfigurations,
  configurationErrorHandling,
};
