/**
 * Test Environment Setup
 * 
 * This script tests that environment variables are properly loaded
 * and the API is accessible.
 */

import { config } from 'dotenv';
import { resolve } from 'path';

// Try to load .env from multiple locations
const envPaths = [
  resolve(process.cwd(), '.env'),
  resolve(process.cwd(), '..', '.env'),
  resolve(process.cwd(), '..', '..', '.env'),
];

console.log('🔍 Testing Environment Setup\n');

// Try each path
let envLoaded = false;
for (const envPath of envPaths) {
  try {
    const result = config({ path: envPath });
    if (!result.error) {
      console.log(`✅ Loaded .env from: ${envPath}`);
      envLoaded = true;
      break;
    }
  } catch (error) {
    // Continue to next path
  }
}

if (!envLoaded) {
  console.log('⚠️  No .env file found in any of these locations:');
  envPaths.forEach(p => console.log(`   - ${p}`));
  console.log('\nUsing default values or system environment variables.\n');
}

// Check environment variables
console.log('\n📋 Environment Variables:');
console.log('─'.repeat(50));

const apiUrl = process.env.AURITE_API_URL || 'http://localhost:8000';
const apiKey = process.env.API_KEY || 'not-set';

console.log(`AURITE_API_URL: ${apiUrl}`);
console.log(`API_KEY: ${apiKey === 'not-set' ? '❌ NOT SET' : `✅ ${apiKey.substring(0, 8)}...${apiKey.substring(apiKey.length - 4)}`}`);

// Test API connectivity
console.log('\n🌐 Testing API Connectivity:');
console.log('─'.repeat(50));

async function testConnection() {
  try {
    const response = await fetch(`${apiUrl}/health`, {
      headers: {
        'X-API-Key': apiKey
      }
    });

    if (response.ok) {
      const data = await response.json();
      console.log(`✅ API is reachable at ${apiUrl}`);
      console.log(`   Response: ${JSON.stringify(data)}`);
    } else {
      console.log(`❌ API returned error: ${response.status} ${response.statusText}`);
      if (response.status === 401) {
        console.log('   This might indicate an invalid API key.');
      }
    }
  } catch (error: any) {
    console.log(`❌ Failed to connect to API: ${error.message}`);
    if (error.code === 'ECONNREFUSED') {
      console.log('   Make sure the Aurite API server is running.');
    }
  }
}

testConnection().then(() => {
  console.log('\n✨ Environment test complete!');
});
