// filepath: /home/wilcoxr/workspace/aurite/framework/frontend/examples/environment-demo.ts
/**
 * Environment Configuration Demo (Refactored)
 *
 * This example demonstrates the new cleaner way to handle environment variables
 * in the Aurite API Client, using the shared example client setup.
 */

import { createExampleClient, runExample, prettyPrint } from './shared/client-setup';
import { createAuriteConfig, getAuriteConfig } from '../src/config/environment';

async function demonstrateEnvironmentConfig() {
  console.log('🌍 Environment Configuration Demo');
  console.log('='.repeat(50));

  // Method 1: Use example client (recommended)
  console.log('\n1. Creating example client from environment variables:');
  try {
    const config = getAuriteConfig();

    console.log(`   Base URL: ${config.baseUrl}`);
    console.log(`   API Key: ${config.apiKey?.substring(0, 8) || '[NOT SET]'}...`);
    console.log(`   Environment: ${config.environment}`);
    console.log(`   Is Development: ${config.isDevelopment}`);

    // Test the client
    console.log('\n   Testing client connection...');
    await createExampleClient();
    console.log('   ✅ Example client created successfully');
  } catch (error) {
    console.error('   ❌ Error creating example client:', error);
  }

  // Method 2: Example client with overrides
  console.log('\n2. Creating example client with config overrides:');
  try {
    const config2 = createAuriteConfig({
      baseUrl: 'http://custom-server:8000',
      apiKey: 'custom-api-key',
      environment: 'development',
    });

    console.log('   ✅ Example client created with custom base URL');
    prettyPrint(config2, 'Custom Config');
  } catch (error) {
    console.error('   ❌ Error creating example client with overrides:', error);
  }

  // Method 3: Show configuration details
  console.log('\n3. Current example client configuration:');
  try {
    const config = getAuriteConfig();

    console.log('   Configuration details:');
    console.log(`   - Base URL: ${config.baseUrl}`);
    console.log(`   - API Key: ${config.apiKey ? '[SET]' : '[NOT SET]'}`);
    console.log(`   - Environment: ${config.environment}`);
    console.log(`   - Development mode: ${config.isDevelopment}`);
    console.log(`   - Test mode: ${config.isTest}`);
    console.log(`   - Production mode: ${config.isProduction}`);
  } catch (error) {
    console.error('   ❌ Error getting configuration:', error);
  }

  console.log('\n✨ Demo completed!');
  console.log('\nKey Benefits of the new approach:');
  console.log('• Automatic .env file loading');
  console.log('• Centralized configuration management');
  console.log('• Type-safe configuration');
  console.log('• Environment-aware defaults');
  console.log('• Easy configuration overrides');
  console.log('• No need for manual dotenv loading in scripts');
}

// Main execution
async function main() {
  await runExample('Environment Configuration Demo', demonstrateEnvironmentConfig);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export { demonstrateEnvironmentConfig };
