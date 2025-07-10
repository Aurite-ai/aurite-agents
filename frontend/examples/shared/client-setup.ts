/**
 * Shared client setup utilities for Aurite API examples
 * 
 * This module provides common client initialization and configuration
 * that can be reused across all examples.
 */

import { createAuriteClient } from '../../src/client/AuriteApiClient';
import type { AuriteApiClient } from '../../src/client/AuriteApiClient';
import { getApiClientConfig, getAuriteConfig } from '../../src/config/environment';

/**
 * Default configuration for examples
 * Uses centralized environment configuration
 */
export const DEFAULT_CONFIG = getApiClientConfig();

/**
 * Create a configured Aurite API client for examples
 * 
 * @param config Optional configuration override
 * @returns Configured API client
 */
export function createExampleClient(config?: Partial<typeof DEFAULT_CONFIG>): AuriteApiClient {
  const finalConfig = getApiClientConfig(config);
  return createAuriteClient(finalConfig.baseUrl, finalConfig.apiKey);
}

/**
 * Common error handler for examples
 * 
 * @param error The error to handle
 * @param context Optional context for the error
 */
export function handleExampleError(error: unknown, context?: string): void {
  const prefix = context ? `[${context}]` : '[Example]';
  
  if (error instanceof Error) {
    console.error(`${prefix} Error:`, error.message);
    
    // If it's an API error, show additional details
    if ('status' in error && 'category' in error) {
      console.error(`${prefix} Status:`, (error as any).status);
      console.error(`${prefix} Category:`, (error as any).category);
      console.error(`${prefix} User Message:`, (error as any).userMessage);
    }
  } else {
    console.error(`${prefix} Unknown error:`, error);
  }
}

/**
 * Utility to add delays between operations (useful for demos)
 * 
 * @param ms Milliseconds to wait
 */
export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Pretty print JSON objects for examples
 * 
 * @param obj Object to print
 * @param label Optional label for the output
 */
export function prettyPrint(obj: any, label?: string): void {
  if (label) {
    console.log(`\n=== ${label} ===`);
  }
  console.log(JSON.stringify(obj, null, 2));
}

/**
 * Common example runner that handles setup and cleanup
 * 
 * @param name Name of the example
 * @param fn Function to run
 */
export async function runExample(name: string, fn: () => Promise<void>): Promise<void> {
  console.log(`\n🚀 Running Example: ${name}`);
  console.log('=' .repeat(50));
  
  try {
    await fn();
    console.log(`\n✅ Example "${name}" completed successfully`);
  } catch (error) {
    console.log(`\n❌ Example "${name}" failed`);
    handleExampleError(error, name);
  }
}
