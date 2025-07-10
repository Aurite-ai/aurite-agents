import { defineConfig } from 'vitest/config';
import { config } from 'dotenv';

// Load environment variables from .env file for tests
config();

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    setupFiles: ['./vitest.setup.ts'],
    // Set test environment
    env: {
      NODE_ENV: 'test',
    },
    // Use our test TypeScript configuration
    typecheck: {
      tsconfig: './tsconfig.test.json',
    },
    // Increase timeout for integration tests
    testTimeout: 30000, // 30 seconds
  },
});
