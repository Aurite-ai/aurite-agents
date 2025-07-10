/**
 * Agent Streaming Example
 * 
 * This example demonstrates real-time streaming of agent responses.
 * Streaming provides immediate feedback as the agent processes requests,
 * calls tools, and generates responses.
 */

import type { StreamEvent } from '../../src/types';
import { createExampleClient, runExample, handleExampleError, delay } from '../shared/client-setup';

async function basicStreaming() {
  const client = createExampleClient();

  console.log('\n📋 Example 1: Basic Agent Streaming');
  
  try {
    console.log('🔄 Starting stream for Weather Agent...');
    
    await client.execution.streamAgent(
      'Weather Agent',
      {
        user_message: 'What is the weather in Tokyo?',
      },
      (event: StreamEvent) => {
        switch (event.type) {
          case 'llm_response_start':
            console.log('🚀 Agent started responding...');
            break;
            
          case 'llm_response':
            // Stream the response content as it arrives
            process.stdout.write(event.data.content);
            break;
            
          case 'llm_response_stop':
            console.log('\n✅ Agent finished responding.');
            break;
            
          case 'tool_call':
            console.log(`\n🔧 Calling tool: ${event.data.name}`);
            if (event.data.arguments) {
              console.log(`   Arguments:`, JSON.stringify(event.data.arguments, null, 2));
            }
            break;
            
          case 'tool_output':
            console.log('📊 Tool output:', JSON.stringify(event.data.output, null, 2));
            break;
            
          case 'error':
            console.error('❌ Stream error:', event.data.message);
            break;
            
          default:
            console.log('📨 Unknown event type:', event.type, event.data);
        }
      }
    );
    
  } catch (error) {
    handleExampleError(error, 'Basic Streaming');
  }
}

async function advancedStreaming() {
  const client = createExampleClient();

  console.log('\n📋 Example 2: Advanced Streaming with Event Tracking');
  
  try {
    let eventCount = 0;
    let toolCalls = 0;
    let responseLength = 0;
    const startTime = Date.now();
    
    console.log('🔄 Starting advanced stream...');
    
    await client.execution.streamAgent(
      'Weather Planning Agent',
      {
        user_message: 'What should I wear in London today? Please save a plan.',
        session_id: 'streaming-demo',
      },
      (event: StreamEvent) => {
        eventCount++;
        
        switch (event.type) {
          case 'llm_response_start':
            console.log(`\n[${eventCount}] 🚀 Response started`);
            break;
            
          case 'llm_response':
            responseLength += event.data.content.length;
            process.stdout.write(event.data.content);
            break;
            
          case 'llm_response_stop':
            const duration = Date.now() - startTime;
            console.log(`\n[${eventCount}] ✅ Response completed`);
            console.log(`   📊 Stats: ${responseLength} chars, ${duration}ms, ${toolCalls} tool calls`);
            break;
            
          case 'tool_call':
            toolCalls++;
            console.log(`\n[${eventCount}] 🔧 Tool Call #${toolCalls}: ${event.data.name}`);
            break;
            
          case 'tool_output':
            console.log(`[${eventCount}] 📊 Tool Result: ${JSON.stringify(event.data.output).substring(0, 100)}...`);
            break;
            
          case 'error':
            console.error(`[${eventCount}] ❌ Error:`, event.data.message);
            break;
        }
      }
    );
    
  } catch (error) {
    handleExampleError(error, 'Advanced Streaming');
  }
}

async function streamingWithCancellation() {
  const client = createExampleClient();

  console.log('\n📋 Example 3: Streaming with Cancellation');
  
  try {
    const controller = new AbortController();
    
    // Cancel the stream after 3 seconds
    setTimeout(() => {
      console.log('\n⏹️  Cancelling stream...');
      controller.abort();
    }, 3000);
    
    console.log('🔄 Starting stream (will cancel in 3 seconds)...');
    
    await client.execution.streamAgent(
      'Weather Agent',
      {
        user_message: 'Tell me a very long story about the weather around the world.',
      },
      (event: StreamEvent) => {
        switch (event.type) {
          case 'llm_response_start':
            console.log('🚀 Stream started...');
            break;
            
          case 'llm_response':
            process.stdout.write(event.data.content);
            break;
            
          case 'llm_response_stop':
            console.log('\n✅ Stream completed normally');
            break;
            
          case 'error':
            console.error('\n❌ Stream error:', event.data.message);
            break;
        }
      }
    );
    
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.log('\n✅ Stream successfully cancelled');
    } else {
      handleExampleError(error, 'Streaming with Cancellation');
    }
  }
}

async function multipleStreams() {
  const client = createExampleClient();

  console.log('\n📋 Example 4: Multiple Concurrent Streams');
  
  const agents = ['Weather Agent', 'Simple Planning Agent'];
  const messages = [
    'What is the weather in Paris?',
    'Create a plan for learning TypeScript',
  ];
  
  try {
    const streamPromises = agents.map((agent, index) => {
      console.log(`🔄 Starting stream ${index + 1} for ${agent}...`);
      
      return client.execution.streamAgent(
        agent,
        { user_message: messages[index] },
        (event: StreamEvent) => {
          const prefix = `[Stream ${index + 1}]`;
          
          switch (event.type) {
            case 'llm_response_start':
              console.log(`${prefix} 🚀 Started`);
              break;
              
            case 'llm_response':
              // For demo, just show first few chars to avoid clutter
              if (event.data.content.length > 0) {
                process.stdout.write(`${prefix[0]}`);
              }
              break;
              
            case 'llm_response_stop':
              console.log(`\n${prefix} ✅ Completed`);
              break;
              
            case 'tool_call':
              console.log(`\n${prefix} 🔧 Tool: ${event.data.name}`);
              break;
              
            case 'error':
              console.error(`\n${prefix} ❌ Error:`, event.data.message);
              break;
          }
        }
      );
    });
    
    await Promise.all(streamPromises);
    console.log('\n✅ All streams completed');
    
  } catch (error) {
    handleExampleError(error, 'Multiple Streams');
  }
}

// Main execution
async function main() {
  await runExample('Basic Streaming', basicStreaming);
  await delay(1000); // Small delay between examples
  
  await runExample('Advanced Streaming', advancedStreaming);
  await delay(1000);
  
  await runExample('Streaming with Cancellation', streamingWithCancellation);
  await delay(1000);
  
  await runExample('Multiple Concurrent Streams', multipleStreams);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export { basicStreaming, advancedStreaming, streamingWithCancellation, multipleStreams };
