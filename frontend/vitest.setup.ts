// Vitest setup file
// This file is run before each test file

import { vi } from 'vitest';

// Load environment variables from .env file
try {
  const dotenv = require('dotenv');
  dotenv.config();
} catch (error) {
  console.warn('Failed to load dotenv for tests:', error);
}

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
