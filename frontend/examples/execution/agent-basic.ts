/**
 * Basic Agent Execution Example
 *
 * This example demonstrates how to run agents and get complete responses.
 * Agents are AI assistants that can use tools and maintain conversation history.
 */

import { createExampleClient, runExample, handleExampleError } from '../shared/client-setup';

async function basicAgentExecution() {
  const client = await createExampleClient();

  // Example 1: Simple agent execution
  console.log('\n📋 Example 1: Basic Agent Execution');
  try {
    const result = await client.execution.runAgent('Weather Agent', {
      user_message: 'What is the weather in San Francisco?',
    });

    console.log('✅ Agent Status:', result.status);
    console.log('📝 Response:', result.final_response?.content);

    // Show conversation history
    if (result.conversation_history && result.conversation_history.length > 0) {
      console.log('\n💬 Conversation History:');
      result.conversation_history.forEach((msg, index) => {
        console.log(`  ${index + 1}. ${msg.role}: ${msg.content || '[tool calls]'}`);
      });
    }
  } catch (error) {
    handleExampleError(error, 'Basic Agent');
  }

  // Example 2: Agent with session ID (conversation history)
  console.log('\n📋 Example 2: Agent with Session History');
  try {
    const sessionId = 'user-session-123';

    // First message
    const result1 = await client.execution.runAgent('Weather Agent', {
      user_message: 'What is the weather in Tokyo?',
      session_id: sessionId,
    });
    console.log('✅ First Response:', result1.final_response?.content);

    // Follow-up message (should remember context)
    const result2 = await client.execution.runAgent('Weather Agent', {
      user_message: 'What about London?',
      session_id: sessionId,
    });
    console.log('✅ Follow-up Response:', result2.final_response?.content);
  } catch (error) {
    handleExampleError(error, 'Session Agent');
  }

  // Example 3: Agent with different configurations
  console.log('\n📋 Example 3: Different Agent Types');
  try {
    // Try a structured output agent
    const structuredResult = await client.execution.runAgent('Structured Output Weather Agent', {
      user_message: 'Get weather for New York',
    });
    console.log('✅ Structured Agent Response:', structuredResult.final_response?.content);
  } catch (error) {
    handleExampleError(error, 'Structured Agent');
  }
}

async function agentErrorHandling() {
  const client = await createExampleClient();

  console.log('\n📋 Example 4: Error Handling');

  // Try to run a non-existent agent
  try {
    await client.execution.runAgent('Non-Existent Agent', {
      user_message: 'Hello',
    });
  } catch (error) {
    console.log('✅ Expected error for non-existent agent:');
    handleExampleError(error, 'Non-Existent Agent');
  }

  // Try with invalid request
  try {
    await client.execution.runAgent('Weather Agent', {} as any);
  } catch (error) {
    console.log('✅ Expected error for invalid request:');
    handleExampleError(error, 'Invalid Request');
  }
}

async function agentStatus() {
  const client = await createExampleClient();

  console.log('\n📋 Example 5: Execution Status');
  try {
    const status = await client.execution.getStatus();
    console.log('✅ Execution Facade Status:', status);
  } catch (error) {
    handleExampleError(error, 'Status Check');
  }
}

// Main execution
async function main() {
  await runExample('Basic Agent Execution', basicAgentExecution);
  await runExample('Agent Error Handling', agentErrorHandling);
  await runExample('Agent Status Check', agentStatus);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export { basicAgentExecution, agentErrorHandling, agentStatus };
