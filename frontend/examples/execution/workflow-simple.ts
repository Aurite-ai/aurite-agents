/**
 * Simple Workflow Execution Example
 *
 * This example demonstrates how to run simple workflows.
 * Simple workflows execute a series of agents in sequence,
 * where each agent receives the output of the previous agent.
 */

import {
  createExampleClient,
  runExample,
  handleExampleError,
  prettyPrint,
} from '../shared/client-setup';

async function basicWorkflowExecution() {
  const client = await createExampleClient();

  console.log('\n📋 Example 1: Basic Simple Workflow');

  try {
    const result = await client.execution.runSimpleWorkflow('Weather Planning Workflow', {
      initial_input: 'What should I wear in London today?',
    });

    console.log('✅ Workflow Status:', result.status);
    console.log('📝 Final Output:', result.final_output);

    // Check if steps exist and display them
    if (result.steps && Array.isArray(result.steps)) {
      console.log('\n📊 Workflow Steps:');
      result.steps.forEach((step, index) => {
        console.log(`  ${index + 1}. ${step.step_name}: ${step.status}`);
        if (step.result) {
          console.log(`     Result: ${JSON.stringify(step.result).substring(0, 100)}...`);
        }
        if (step.error) {
          console.log(`     Error: ${step.error}`);
        }
      });
    } else {
      console.log('ℹ️  No step information available in workflow response');
    }

    // Show error message if workflow failed
    if (result.error_message) {
      console.log('❌ Workflow Error:', result.error_message);
    }
  } catch (error) {
    handleExampleError(error, 'Basic Workflow');
  }
}

async function workflowWithDifferentInputs() {
  const client = await createExampleClient();

  console.log('\n📋 Example 2: Workflow with Different Input Types');

  const testInputs = [
    {
      name: 'Weather Query',
      input: 'What should I wear in Tokyo tomorrow?',
    },
    {
      name: 'Travel Planning',
      input: 'Plan what to pack for a trip to New York in winter',
    },
    {
      name: 'Activity Planning',
      input: 'What outdoor activities are good for San Francisco weather?',
    },
  ];

  for (const test of testInputs) {
    try {
      console.log(`\n🔄 Testing: ${test.name}`);
      console.log(`   Input: "${test.input}"`);

      const result = await client.execution.runSimpleWorkflow('Weather Planning Workflow', {
        initial_input: test.input,
      });

      console.log(`   ✅ Status: ${result.status}`);
      if (result.final_output) {
        const output =
          typeof result.final_output === 'string'
            ? result.final_output
            : JSON.stringify(result.final_output);
        console.log(`   📝 Output: ${output.substring(0, 150)}...`);
      }
    } catch (error) {
      console.log(`   ❌ Failed: ${test.name}`);
      handleExampleError(error, test.name);
    }
  }
}

async function workflowErrorHandling() {
  const client = await createExampleClient();

  console.log('\n📋 Example 3: Workflow Error Handling');

  // Test 1: Non-existent workflow
  try {
    await client.execution.runSimpleWorkflow('Non-Existent Workflow', {
      initial_input: 'Test input',
    });
  } catch (error) {
    console.log('✅ Expected error for non-existent workflow:');
    handleExampleError(error, 'Non-Existent Workflow');
  }

  // Test 2: Invalid input format
  try {
    await client.execution.runSimpleWorkflow('Weather Planning Workflow', {} as any);
  } catch (error) {
    console.log('\n✅ Expected error for invalid input:');
    handleExampleError(error, 'Invalid Input');
  }

  // Test 3: Empty input
  try {
    const result = await client.execution.runSimpleWorkflow('Weather Planning Workflow', {
      initial_input: '',
    });

    console.log('\n📝 Result with empty input:');
    console.log('   Status:', result.status);
    console.log('   Output:', result.final_output);
  } catch (error) {
    console.log('\n✅ Error with empty input:');
    handleExampleError(error, 'Empty Input');
  }
}

async function workflowComparison() {
  const client = await createExampleClient();

  console.log('\n📋 Example 4: Comparing Workflow vs Direct Agent');

  const userMessage = 'What should I wear in Paris today?';

  try {
    // Run direct agent
    console.log('🔄 Running direct Weather Agent...');
    const agentResult = await client.execution.runAgent('Weather Agent', {
      user_message: userMessage,
    });

    console.log('✅ Direct Agent Result:');
    console.log('   Status:', agentResult.status);
    console.log('   Response:', `${agentResult.final_response?.content?.substring(0, 200)}...`);

    // Run workflow
    console.log('\n🔄 Running Weather Planning Workflow...');
    const workflowResult = await client.execution.runSimpleWorkflow('Weather Planning Workflow', {
      initial_input: userMessage,
    });

    console.log('✅ Workflow Result:');
    console.log('   Status:', workflowResult.status);
    const output =
      typeof workflowResult.final_output === 'string'
        ? workflowResult.final_output
        : JSON.stringify(workflowResult.final_output);
    console.log('   Output:', `${output.substring(0, 200)}...`);

    console.log('\n📊 Comparison:');
    console.log('   - Direct agent: Faster, single response');
    console.log('   - Workflow: More comprehensive, multi-step processing');
  } catch (error) {
    handleExampleError(error, 'Workflow Comparison');
  }
}

async function workflowWithComplexInput() {
  const client = await createExampleClient();

  console.log('\n📋 Example 5: Workflow with Complex Input');

  try {
    // Test with a complex, multi-part request
    const complexInput = `
      I'm planning a business trip to London next week.
      I need to know:
      1. What the weather will be like
      2. What professional attire to pack
      3. Whether I need an umbrella or rain gear
      4. Any seasonal considerations for business meetings

      Please create a comprehensive packing plan.
    `;

    console.log('🔄 Running workflow with complex input...');

    const result = await client.execution.runSimpleWorkflow('Weather Planning Workflow', {
      initial_input: complexInput.trim(),
    });

    console.log('✅ Complex Input Result:');
    console.log('   Status:', result.status);

    if (result.final_output) {
      console.log('\n📝 Detailed Output:');
      prettyPrint(result.final_output, 'Workflow Final Output');
    }

    if (result.steps && result.steps.length > 0) {
      console.log('\n📊 Step-by-Step Breakdown:');
      result.steps.forEach((step, index) => {
        console.log(`\n   Step ${index + 1}: ${step.step_name}`);
        console.log(`   Status: ${step.status}`);
        if (step.result) {
          const stepResult =
            typeof step.result === 'string' ? step.result : JSON.stringify(step.result);
          console.log(`   Result: ${stepResult.substring(0, 150)}...`);
        }
      });
    }
  } catch (error) {
    handleExampleError(error, 'Complex Input Workflow');
  }
}

// Main execution
async function main() {
  await runExample('Basic Workflow Execution', basicWorkflowExecution);
  await runExample('Workflow with Different Inputs', workflowWithDifferentInputs);
  await runExample('Workflow Error Handling', workflowErrorHandling);
  await runExample('Workflow vs Agent Comparison', workflowComparison);
  await runExample('Workflow with Complex Input', workflowWithComplexInput);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export {
  basicWorkflowExecution,
  workflowWithDifferentInputs,
  workflowErrorHandling,
  workflowComparison,
  workflowWithComplexInput,
};
