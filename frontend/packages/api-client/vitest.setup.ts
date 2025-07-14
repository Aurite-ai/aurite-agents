// Vitest setup file
// This file is run before each test file

import { vi } from 'vitest';
import { config } from 'dotenv';
import { resolve } from 'path';

// Load environment variables from multiple locations
// First try local .env, then fallback to frontend root
const localEnvPath = resolve(__dirname, '.env');
const rootEnvPath = resolve(__dirname, '../../.env');

// Try local .env first
const result = config({ path: localEnvPath });
if (result.error) {
  // Fallback to frontend root .env
  config({ path: rootEnvPath });
  console.log('Using frontend root .env file');
} else {
  console.log('Using local api-client .env file');
}

// Log environment variable loading status
console.log('Environment variables loaded:');
console.log('- AURITE_API_URL:', process.env.AURITE_API_URL ? '✓' : '✗');
console.log('- API_KEY:', process.env.API_KEY ? '✓ (hidden)' : '✗');

// Check if this is an integration test by looking at the test file path
const isIntegrationTest = process.argv.some(arg => arg.includes('integration'));

if (isIntegrationTest) {
  // For integration tests, use real fetch from undici
  try {
    const undici = require('undici');
    Object.assign(globalThis, {
      fetch: undici.fetch,
      Headers: undici.Headers,
      Request: undici.Request,
      Response: undici.Response
    });
    console.log('✓ Loaded undici for integration tests');
  } catch (error) {
    console.warn('Failed to load undici for integration tests:', error);
    // Fallback to Node.js built-in fetch if available (Node 18+)
    if (typeof globalThis.fetch === 'undefined') {
      (globalThis as any).fetch = vi.fn();
    }
  }
} else {
  // For unit tests, only set up fetch if it doesn't exist
  // Individual tests will mock it as needed
  if (typeof globalThis.fetch === 'undefined') {
    (globalThis as any).fetch = vi.fn();
  }
}
