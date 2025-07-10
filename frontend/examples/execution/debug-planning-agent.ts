/**
 * Debugging the Weather Planning Workflow Step 2 Agent
 */

import { createExampleClient, runExample, handleExampleError } from '../shared/client-setup';

async function debugPlanningAgent() {
  const client = await createExampleClient();

  console.log('\n📋 Debugging: Weather Planning Workflow Step 2');

  try {
    const result = await client.execution.runAgent('Weather Planning Workflow Step 2', {
      user_message: 'The weather in London is 15C and rainy.',
    });

    console.log('✅ Agent Status:', result.status);
    console.log('📝 Response:', result.final_response?.content);

    if (result.conversation_history) {
      console.log('\n💬 Conversation History:');
      result.conversation_history.forEach((msg, index) => {
        console.log(`  ${index + 1}. ${msg.role}: ${msg.content || '[tool calls]'}`);
      });
    }
  } catch (error) {
    handleExampleError(error, 'Debug Planning Agent');
  }
}

async function main() {
  await runExample('Debug Planning Agent', debugPlanningAgent);
}

main().catch(console.error);
