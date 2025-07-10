/**
 * MCP Tool Execution Example
 *
 * This example demonstrates how to call MCP tools directly:
 * - List available tools and their schemas
 * - Call tools with different argument types
 * - Handle tool errors and responses
 * - Compare tool results
 */

import {
  createExampleClient,
  runExample,
  handleExampleError,
  prettyPrint,
} from '../shared/client-setup';

async function listAndInspectTools() {
  const client = await createExampleClient();

  console.log('\n📋 Example 1: List and Inspect Tools');

  try {
    // Make sure we have some tools available
    try {
      await client.host.registerServerByName('weather_server');
      await client.host.registerServerByName('planning_server');
    } catch (error) {
      console.log('ℹ️  Servers may already be registered');
    }

    const tools = await client.host.listTools();
    console.log(`✅ Found ${tools.length} available tools:`);

    tools.forEach((tool, index) => {
      console.log(`\n🔧 Tool ${index + 1}: ${tool.name}`);
      console.log(`   Description: ${tool.description || 'No description provided'}`);

      if (tool.inputSchema) {
        console.log('   Input Schema:');
        console.log('   ', JSON.stringify(tool.inputSchema, null, 4));
      }
    });
  } catch (error) {
    handleExampleError(error, 'List Tools');
  }
}

async function basicToolCalls() {
  const client = await createExampleClient();

  console.log('\n📋 Example 2: Basic Tool Calls');

  try {
    // Ensure weather server is registered
    try {
      await client.host.registerServerByName('weather_server');
    } catch (error) {
      console.log('ℹ️  Weather server may already be registered');
    }

    // Test different locations
    const locations = ['New York', 'London', 'Tokyo', 'San Francisco'];

    for (const location of locations) {
      try {
        console.log(`\n🌤️  Getting weather for ${location}...`);

        const result = await client.host.callTool('weather_lookup', {
          location,
        });

        console.log('✅ Tool Result:');
        if (result.content && result.content.length > 0) {
          result.content.forEach((item, index) => {
            console.log(`   Content ${index + 1}: ${item.text || JSON.stringify(item)}`);
          });
        }

        if (result.isError) {
          console.log('⚠️  Tool reported an error');
        }
      } catch (error) {
        console.log(`❌ Failed to get weather for ${location}:`);
        handleExampleError(error, `Weather ${location}`);
      }
    }
  } catch (error) {
    handleExampleError(error, 'Basic Tool Calls');
  }
}

async function planningToolCalls() {
  const client = await createExampleClient();

  console.log('\n📋 Example 3: Planning Tool Calls');

  try {
    // Ensure planning server is registered
    try {
      await client.host.registerServerByName('planning_server');
    } catch (error) {
      console.log('ℹ️  Planning server may already be registered');
    }

    // Test saving a plan
    console.log('💾 Saving a plan...');
    try {
      // Using a template literal for a clear, multi-line string plan.
      const planContent = `
# Weekend Trip to Paris

## Steps
- Book flight tickets
- Reserve hotel accommodation
- Plan daily itinerary
- Pack appropriate clothing
- Arrange airport transportation

## Notes
Remember to check weather forecast before packing
      `;
      const saveResult = await client.host.callTool('save_plan', {
        plan_name: 'weekend-trip-to-paris',
        plan_content: planContent,
        tags: ['paris', 'weekend', 'travel'],
      });

      console.log('✅ Plan saved successfully:');
      prettyPrint(saveResult, 'Save Plan Result');
    } catch (error) {
      handleExampleError(error, 'Save Plan');
    }

    // Test listing plans
    console.log('\n📋 Listing saved plans...');
    try {
      const listResult = await client.host.callTool('list_plans', {});

      console.log('✅ Plans retrieved:');
      prettyPrint(listResult, 'List Plans Result');
    } catch (error) {
      handleExampleError(error, 'List Plans');
    }
  } catch (error) {
    handleExampleError(error, 'Planning Tool Calls');
  }
}

async function toolErrorHandling() {
  const client = await createExampleClient();

  console.log('\n📋 Example 4: Tool Error Handling');

  try {
    // Ensure weather server is registered
    try {
      await client.host.registerServerByName('weather_server');
    } catch (error) {
      console.log('ℹ️  Weather server may already be registered');
    }

    // Test 1: Call non-existent tool
    try {
      await client.host.callTool('non_existent_tool', { arg: 'value' });
    } catch (error) {
      console.log('✅ Expected error for non-existent tool:');
      handleExampleError(error, 'Non-existent Tool');
    }

    // Test 2: Call tool with invalid arguments
    try {
      await client.host.callTool('weather_lookup', { invalid_arg: 'value' });
    } catch (error) {
      console.log('\n✅ Expected error for invalid arguments:');
      handleExampleError(error, 'Invalid Arguments');
    }

    // Test 3: Call tool with missing required arguments
    try {
      await client.host.callTool('weather_lookup', {});
    } catch (error) {
      console.log('\n✅ Expected error for missing arguments:');
      handleExampleError(error, 'Missing Arguments');
    }

    // Test 4: Call tool with unsupported location (should handle gracefully)
    try {
      const result = await client.host.callTool('weather_lookup', {
        location: 'Atlantis',
      });

      console.log('\n📝 Result for unsupported location:');
      prettyPrint(result, 'Unsupported Location Result');
    } catch (error) {
      console.log('\n✅ Error for unsupported location:');
      handleExampleError(error, 'Unsupported Location');
    }
  } catch (error) {
    handleExampleError(error, 'Tool Error Handling');
  }
}

async function concurrentToolCalls() {
  const client = await createExampleClient();

  console.log('\n📋 Example 5: Concurrent Tool Calls');

  try {
    // Ensure weather server is registered
    try {
      await client.host.registerServerByName('weather_server');
    } catch (error) {
      console.log('ℹ️  Weather server may already be registered');
    }

    const locations = ['New York', 'London', 'Tokyo', 'Paris'];

    console.log('🔄 Making concurrent weather requests...');
    const startTime = Date.now();

    const promises = locations.map(location =>
      client.host
        .callTool('weather_lookup', { location })
        .then(result => ({ location, result, success: true }))
        .catch(error => ({ location, error, success: false }))
    );

    const results = await Promise.all(promises);
    const duration = Date.now() - startTime;

    console.log(`✅ All requests completed in ${duration}ms`);

    results.forEach(item => {
      if (item.success && 'result' in item) {
        console.log(`\n🌤️  ${item.location}:`);
        if (item.result.content && item.result.content[0]) {
          console.log(`   ${item.result.content[0].text}`);
        }
      } else if ('error' in item) {
        console.log(`\n❌ ${item.location}: Failed`);
        if (item.error) {
          console.log(`   Error: ${item.error.message}`);
        }
      }
    });
  } catch (error) {
    handleExampleError(error, 'Concurrent Tool Calls');
  }
}

async function toolResponseAnalysis() {
  const client = await createExampleClient();

  console.log('\n📋 Example 6: Tool Response Analysis');

  try {
    // Ensure servers are registered
    try {
      await client.host.registerServerByName('weather_server');
      await client.host.registerServerByName('planning_server');
    } catch (error) {
      console.log('ℹ️  Servers may already be registered');
    }

    // Analyze different tool response formats
    const toolTests = [
      {
        name: 'Weather Tool',
        tool: 'weather_lookup',
        args: { location: 'San Francisco' },
      },
      {
        name: 'Current Time Tool',
        tool: 'current_time',
        args: {},
      },
      {
        name: 'List Plans Tool',
        tool: 'list_plans',
        args: {},
      },
    ];

    for (const test of toolTests) {
      try {
        console.log(`\n🔍 Analyzing ${test.name}...`);

        const result = await client.host.callTool(test.tool, test.args);

        console.log('📊 Response Analysis:');
        console.log(`   Content items: ${result.content?.length || 0}`);
        console.log(`   Is error: ${result.isError || false}`);

        if (result.content) {
          result.content.forEach((item, index) => {
            console.log(`   Content ${index + 1}:`);
            console.log(`     Type: ${item.type || 'unknown'}`);
            console.log(`     Text length: ${item.text?.length || 0} chars`);
            if (item.text) {
              console.log(`     Preview: ${item.text.substring(0, 50)}...`);
            }
          });
        }
      } catch (error) {
        console.log(`❌ ${test.name} failed:`);
        handleExampleError(error, test.name);
      }
    }
  } catch (error) {
    handleExampleError(error, 'Tool Response Analysis');
  }
}

async function toolPerformanceTest() {
  const client = await createExampleClient();

  console.log('\n📋 Example 7: Tool Performance Test');

  try {
    // Ensure weather server is registered
    try {
      await client.host.registerServerByName('weather_server');
    } catch (error) {
      console.log('ℹ️  Weather server may already be registered');
    }

    const testRuns = 5;
    const location = 'New York';

    console.log(`🏃 Running ${testRuns} performance tests for weather_lookup...`);

    const times: number[] = [];

    for (let i = 0; i < testRuns; i++) {
      const startTime = Date.now();

      try {
        await client.host.callTool('weather_lookup', { location });
        const duration = Date.now() - startTime;
        times.push(duration);
        console.log(`   Run ${i + 1}: ${duration}ms`);
      } catch (error) {
        console.log(`   Run ${i + 1}: Failed`);
        handleExampleError(error, `Performance Test ${i + 1}`);
      }
    }

    if (times.length > 0) {
      const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
      const minTime = Math.min(...times);
      const maxTime = Math.max(...times);

      console.log('\n📊 Performance Summary:');
      console.log(`   Average: ${avgTime.toFixed(2)}ms`);
      console.log(`   Minimum: ${minTime}ms`);
      console.log(`   Maximum: ${maxTime}ms`);
      console.log(`   Successful runs: ${times.length}/${testRuns}`);
    }
  } catch (error) {
    handleExampleError(error, 'Tool Performance Test');
  }
}

// Main execution
async function main() {
  await runExample('List and Inspect Tools', listAndInspectTools);
  await runExample('Basic Tool Calls', basicToolCalls);
  await runExample('Planning Tool Calls', planningToolCalls);
  await runExample('Tool Error Handling', toolErrorHandling);
  await runExample('Concurrent Tool Calls', concurrentToolCalls);
  await runExample('Tool Response Analysis', toolResponseAnalysis);
  await runExample('Tool Performance Test', toolPerformanceTest);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export {
  listAndInspectTools,
  basicToolCalls,
  planningToolCalls,
  toolErrorHandling,
  concurrentToolCalls,
  toolResponseAnalysis,
  toolPerformanceTest,
};
