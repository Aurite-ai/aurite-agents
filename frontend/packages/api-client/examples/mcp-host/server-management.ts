/**
 * MCP Server Management Example
 *
 * This example demonstrates how to manage MCP servers:
 * - Register servers by name (pre-configured)
 * - Register servers with custom configuration
 * - Unregister servers
 * - Check host status
 */

import { createExampleClient, runExample, handleExampleError } from '../shared/client-setup';

async function hostStatus() {
  const client = await createExampleClient();

  console.log('\n📋 Example 1: MCP Host Status');

  try {
    const status = await client.host.getStatus();
    console.log('✅ Host Status:', status.status);
    console.log('🔧 Available Tools:', status.tool_count);
  } catch (error) {
    handleExampleError(error, 'Host Status');
  }
}

async function registerServerByName() {
  const client = await createExampleClient();

  console.log('\n📋 Example 2: Register Server by Name');

  try {
    // Register a pre-configured server
    console.log('🔄 Registering weather_server...');
    const result = await client.host.registerServerByName('weather_server');

    console.log('✅ Registration Result:');
    console.log('   Status:', result.status);
    console.log('   Server Name:', result.name);

    // Check tools after registration
    const tools = await client.host.listTools();
    console.log(`🔧 Tools now available: ${tools.length}`);
    tools.forEach(tool => {
      console.log(`   - ${tool.name}: ${tool.description || 'No description'}`);
    });
  } catch (error) {
    handleExampleError(error, 'Register by Name');
  }
}

async function registerServerByConfig() {
  const client = await createExampleClient();

  console.log('\n📋 Example 3: Register Server by Configuration');

  try {
    // Example custom server configuration
    const customConfig = {
      name: 'custom_test_server',
      server_path: '/path/to/custom/server.py',
      transport_type: 'stdio' as const,
      capabilities: ['tools'],
      timeout: 30,
      description: 'A custom test server for demonstration',
    };

    console.log('🔄 Registering custom server...');
    console.log('   Config:', JSON.stringify(customConfig, null, 2));

    const result = await client.host.registerServerByConfig(customConfig);

    console.log('✅ Custom Registration Result:');
    console.log('   Status:', result.status);
    console.log('   Server Name:', result.name);
  } catch (error) {
    // This is expected to fail since the server path doesn't exist
    console.log('✅ Expected error for non-existent server path:');
    handleExampleError(error, 'Custom Server Registration');
  }
}

async function unregisterServer() {
  const client = await createExampleClient();

  console.log('\n📋 Example 4: Unregister Server');

  try {
    // First, make sure weather_server is registered
    try {
      await client.host.registerServerByName('weather_server');
      console.log('✅ Weather server registered for unregistration test');
    } catch (error) {
      console.log('ℹ️  Weather server may already be registered');
    }

    // Now unregister it
    console.log('🔄 Unregistering weather_server...');
    const result = await client.host.unregisterServer('weather_server');

    console.log('✅ Unregistration Result:');
    console.log('   Status:', result.status);
    console.log('   Server Name:', result.name);

    // Check tools after unregistration
    const tools = await client.host.listTools();
    console.log(`🔧 Tools remaining: ${tools.length}`);
  } catch (error) {
    handleExampleError(error, 'Unregister Server');
  }
}

async function serverLifecycleDemo() {
  const client = await createExampleClient();

  console.log('\n📋 Example 5: Complete Server Lifecycle');

  try {
    // Step 1: Check initial status
    console.log('🔄 Step 1: Initial status');
    let status = await client.host.getStatus();
    console.log(`   Initial tool count: ${status.tool_count}`);

    // Step 2: Register server
    console.log('\n🔄 Step 2: Register weather server');
    await client.host.registerServerByName('weather_server');

    status = await client.host.getStatus();
    console.log(`   Tool count after registration: ${status.tool_count}`);

    // Step 3: List tools
    console.log('\n🔄 Step 3: List available tools');
    const tools = await client.host.listTools();
    console.log(`   Available tools: ${tools.map(t => t.name).join(', ')}`);

    // Step 4: Use a tool (if available)
    if (tools.some(t => t.name === 'weather_server-weather_lookup')) {
      console.log('\n🔄 Step 4: Test tool functionality');
      const toolResult = await client.host.callTool('weather_server-weather_lookup', {
        location: 'San Francisco',
      });
      console.log('   Tool result:', `${JSON.stringify(toolResult).substring(0, 100)}...`);
    }

    // Step 5: Unregister server
    console.log('\n🔄 Step 5: Unregister server');
    await client.host.unregisterServer('weather_server');

    status = await client.host.getStatus();
    console.log(`   Final tool count: ${status.tool_count}`);

    console.log('\n✅ Complete lifecycle demonstrated successfully');
  } catch (error) {
    handleExampleError(error, 'Server Lifecycle');
  }
}

async function multipleServerManagement() {
  const client = await createExampleClient();

  console.log('\n📋 Example 6: Multiple Server Management');

  const servers = ['weather_server', 'planning_server'];

  try {
    // Register multiple servers
    console.log('🔄 Registering multiple servers...');
    for (const serverName of servers) {
      try {
        const result = await client.host.registerServerByName(serverName);
        console.log(`   ✅ ${serverName}: ${result.status}`);
      } catch (error) {
        console.log(`   ❌ ${serverName}: Failed to register`);
        handleExampleError(error, `Register ${serverName}`);
      }
    }

    // Check combined tool count
    const status = await client.host.getStatus();
    console.log(`\n🔧 Total tools from all servers: ${status.tool_count}`);

    const tools = await client.host.listTools();
    console.log('📋 All available tools:');
    tools.forEach(tool => {
      console.log(`   - ${tool.name}: ${tool.description || 'No description'}`);
    });

    // Unregister all servers
    console.log('\n🔄 Cleaning up - unregistering all servers...');
    for (const serverName of servers) {
      try {
        await client.host.unregisterServer(serverName);
        console.log(`   ✅ ${serverName}: Unregistered`);
      } catch (error) {
        console.log(`   ⚠️  ${serverName}: May not have been registered`);
      }
    }
  } catch (error) {
    handleExampleError(error, 'Multiple Server Management');
  }
}

async function errorHandlingDemo() {
  const client = await createExampleClient();

  console.log('\n📋 Example 7: Error Handling Scenarios');

  // Test 1: Register non-existent server
  try {
    await client.host.registerServerByName('non_existent_server');
  } catch (error) {
    console.log('✅ Expected error for non-existent server:');
    handleExampleError(error, 'Non-existent Server');
  }

  // Test 2: Unregister non-registered server
  try {
    await client.host.unregisterServer('never_registered_server');
  } catch (error) {
    console.log('\n✅ Expected error for non-registered server:');
    handleExampleError(error, 'Non-registered Server');
  }

  // Test 3: Register server twice
  try {
    await client.host.registerServerByName('weather_server');
    console.log('✅ First registration successful');

    await client.host.registerServerByName('weather_server');
    console.log('✅ Second registration (may succeed or fail depending on implementation)');
  } catch (error) {
    console.log('\n✅ Expected behavior for duplicate registration:');
    handleExampleError(error, 'Duplicate Registration');
  } finally {
    // Clean up
    try {
      await client.host.unregisterServer('weather_server');
    } catch (error) {
      // Ignore cleanup errors
    }
  }
}

// Main execution
async function main() {
  await runExample('Host Status Check', hostStatus);
  await runExample('Register Server by Name', registerServerByName);
  await runExample('Register Server by Config', registerServerByConfig);
  await runExample('Unregister Server', unregisterServer);
  await runExample('Server Lifecycle Demo', serverLifecycleDemo);
  await runExample('Multiple Server Management', multipleServerManagement);
  await runExample('Error Handling Demo', errorHandlingDemo);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export {
  hostStatus,
  registerServerByName,
  registerServerByConfig,
  unregisterServer,
  serverLifecycleDemo,
  multipleServerManagement,
  errorHandlingDemo,
};
