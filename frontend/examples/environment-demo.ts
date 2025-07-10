/**
 * Environment Configuration Demo
 * 
 * This example demonstrates the new cleaner way to handle environment variables
 * in the Aurite API Client. It shows different ways to create clients using
 * the centralized environment configuration.
 */

import { 
  createAuriteClientFromEnv, 
  createAuriteClient,
  getAuriteConfig,
  getApiClientConfig 
} from '../src/index';

async function demonstrateEnvironmentConfig() {
  console.log('🌍 Environment Configuration Demo');
  console.log('=' .repeat(50));

  // Method 1: Use environment configuration directly (recommended)
  console.log('\n1. Creating client from environment variables:');
  try {
    const client1 = await createAuriteClientFromEnv();
    const config = getAuriteConfig();
    
    console.log(`   Base URL: ${config.baseUrl}`);
    console.log(`   API Key: ${config.apiKey.substring(0, 8)}...`);
    console.log(`   Environment: ${config.environment}`);
    console.log(`   Is Development: ${config.isDevelopment}`);
    
    // Test the client
    console.log('\n   Testing client connection...');
    // Note: This would normally make an actual API call
    console.log('   ✅ Client created successfully');
    
  } catch (error) {
    console.error('   ❌ Error creating client:', error);
  }

  // Method 2: Use environment config with overrides
  console.log('\n2. Creating client with environment config + overrides:');
  try {
    const client2 = await createAuriteClientFromEnv({
      baseUrl: 'http://custom-server:8000'
    });
    
    console.log('   ✅ Client created with custom base URL');
    
  } catch (error) {
    console.error('   ❌ Error creating client with overrides:', error);
  }

  // Method 3: Traditional method (still supported)
  console.log('\n3. Traditional client creation (still works):');
  try {
    const apiConfig = getApiClientConfig();
    const client3 = createAuriteClient(apiConfig.baseUrl, apiConfig.apiKey);
    
    console.log('   ✅ Client created using traditional method');
    
  } catch (error) {
    console.error('   ❌ Error creating traditional client:', error);
  }

  // Method 4: Show configuration details
  console.log('\n4. Current environment configuration:');
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

// Run the demo
demonstrateEnvironmentConfig().catch(console.error);
