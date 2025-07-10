/**
 * Debug script to understand unhandled promise rejections in BaseClient tests
 */

import { BaseClient } from '../src/client/BaseClient';
import { ApiConfig } from '../src/types';

class TestableBaseClient extends BaseClient {
  public async testRequest<T>(
    method: string,
    path: string,
    body?: any,
    options?: any
  ): Promise<T> {
    return this.request<T>(method, path, body, options);
  }
}

async function testTimeoutScenario() {
  console.log('Testing timeout scenario...');

  const client = new TestableBaseClient({
    baseUrl: 'http://localhost:8000',
    apiKey: 'test-key'
  });

  // Mock fetch to simulate timeout
  (globalThis as any).fetch = (url: string, options: any) => {
    return new Promise((resolve, reject) => {
      options.signal.addEventListener('abort', () => {
        const error = new Error('The operation was aborted');
        error.name = 'AbortError';
        reject(error);
      });
    });
  };

  try {
    // This should timeout after 5 seconds
    await client.testRequest('GET', '/test', undefined, { timeout: 5000 });
  } catch (error) {
    console.log('Caught error:', error);
  }

  // Wait a bit to see if any unhandled rejections occur
  await new Promise(resolve => setTimeout(resolve, 1000));
}

// Handle unhandled rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

testTimeoutScenario().then(() => {
  console.log('Test completed');
  process.exit(0);
}).catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
