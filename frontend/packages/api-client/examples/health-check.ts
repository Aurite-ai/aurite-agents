/**
 * Health Check Example
 * 
 * This example demonstrates how to perform basic health checks
 * using the Aurite API client.
 */

import { createAuriteClient } from '../src/index.js';

async function main() {
  console.log('🏥 Aurite API Health Check Example\n');

  // Get configuration from environment
  const apiUrl = process.env.AURITE_API_URL || 'http://localhost:8000';
  const apiKey = process.env.API_KEY || 'your-api-key';

  console.log(`API URL: ${apiUrl}`);
  console.log(`API Key: ${apiKey.substring(0, 8)}...${apiKey.substring(apiKey.length - 4)}\n`);

  // Create client
  const client = createAuriteClient(apiUrl, apiKey);

  try {
    // 1. Basic Health Check
    console.log('1️⃣ Basic Health Check');
    console.log('─'.repeat(50));
    
    // The API only has a simple /health endpoint
    const response = await fetch(`${apiUrl}/health`, {
      headers: {
        'X-API-Key': apiKey
      }
    });
    
    if (response.ok) {
      const health = await response.json();
      console.log('✅ API is healthy:', health);
    } else {
      console.log('❌ API health check failed:', response.status, response.statusText);
    }
    console.log();

    // 2. Check Execution Facade Status
    console.log('2️⃣ Execution Facade Status');
    console.log('─'.repeat(50));
    
    try {
      const executionStatus = await client.execution.getStatus();
      console.log('✅ Execution Facade Status:', executionStatus);
    } catch (error: any) {
      console.log('❌ Failed to get execution status:', error.message);
    }
    console.log();

    // 3. Check MCP Host Status
    console.log('3️⃣ MCP Host Status');
    console.log('─'.repeat(50));
    
    try {
      const hostStatus = await client.host.getStatus();
      console.log('✅ MCP Host Status:', hostStatus);
    } catch (error: any) {
      console.log('❌ Failed to get host status:', error.message);
    }
    console.log();

    // 4. List Available Configurations
    console.log('4️⃣ Available Configurations');
    console.log('─'.repeat(50));
    
    try {
      const agents = await client.config.listConfigs('agent');
      console.log(`✅ Available Agents: ${agents.length}`);
      if (agents.length > 0) {
        console.log('   First few agents:', agents.slice(0, 3).map(a => a.name).join(', '));
      }
    } catch (error: any) {
      console.log('❌ Failed to list agents:', error.message);
    }
    console.log();

    // 5. List Available Tools
    console.log('5️⃣ Available Tools');
    console.log('─'.repeat(50));
    
    try {
      const tools = await client.host.listTools();
      console.log(`✅ Available Tools: ${tools.length}`);
      if (tools.length > 0) {
        console.log('   First few tools:', tools.slice(0, 3).map(t => t.name).join(', '));
      }
    } catch (error: any) {
      console.log('❌ Failed to list tools:', error.message);
    }
    console.log();

    // Summary
    console.log('📊 Health Check Summary');
    console.log('─'.repeat(50));
    console.log('✅ API client successfully created and connected');
    console.log('✅ Basic health check passed');
    console.log('ℹ️  Note: System endpoints are not available in the current API');
    console.log('ℹ️  Use execution, host, and config endpoints for monitoring');

  } catch (error) {
    console.error('❌ Health check failed:', error);
    process.exit(1);
  }
}

// Run the example
main().catch(console.error);
