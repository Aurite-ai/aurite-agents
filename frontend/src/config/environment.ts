/**
 * Centralized environment configuration for the Aurite API Client
 * 
 * This module handles:
 * - Loading environment variables from .env files
 * - Providing typed configuration objects
 * - Environment validation and defaults
 * - Different environment handling (dev, test, prod)
 */

import { config } from 'dotenv';
import { resolve } from 'path';

// Load environment variables from .env file
// This will automatically load from the frontend/.env file
config({ path: resolve(process.cwd(), '.env') });

/**
 * Environment types
 */
export type Environment = 'development' | 'test' | 'production';

/**
 * Aurite API configuration interface
 */
export interface AuriteConfig {
  /** Base URL for the Aurite API */
  baseUrl: string;
  /** API key for authentication */
  apiKey: string;
  /** Current environment */
  environment: Environment;
  /** Whether we're in development mode */
  isDevelopment: boolean;
  /** Whether we're in test mode */
  isTest: boolean;
  /** Whether we're in production mode */
  isProduction: boolean;
}

/**
 * Get the current environment
 */
function getEnvironment(): Environment {
  const env = process.env.NODE_ENV?.toLowerCase();
  
  switch (env) {
    case 'test':
      return 'test';
    case 'production':
    case 'prod':
      return 'production';
    default:
      return 'development';
  }
}

/**
 * Get environment variable with validation
 */
function getEnvVar(name: string, defaultValue?: string, required: boolean = false): string {
  const value = process.env[name] || defaultValue;
  
  if (required && !value) {
    throw new Error(`Required environment variable ${name} is not set`);
  }
  
  return value || '';
}

/**
 * Default configuration values based on environment
 */
function getDefaultConfig(environment: Environment): Partial<AuriteConfig> {
  const baseDefaults = {
    baseUrl: 'http://localhost:8000',
    apiKey: 'your_test_key',
  };

  switch (environment) {
    case 'test':
      return {
        ...baseDefaults,
        apiKey: 'test_key_for_testing',
      };
    case 'production':
      return {
        baseUrl: 'https://api.aurite.dev', // Example production URL
        apiKey: '', // Should be provided via environment variable in production
      };
    default: // development
      return baseDefaults;
  }
}

/**
 * Create and validate the configuration
 */
function createConfig(): AuriteConfig {
  const environment = getEnvironment();
  const defaults = getDefaultConfig(environment);
  
  // Get configuration from environment variables with fallbacks
  const baseUrl = getEnvVar('AURITE_API_BASE_URL', defaults.baseUrl);
  const apiKey = getEnvVar('AURITE_API_KEY', defaults.apiKey, environment === 'production');
  
  // Validate required fields
  if (!baseUrl) {
    throw new Error('AURITE_API_BASE_URL must be provided');
  }
  
  if (environment === 'production' && !apiKey) {
    throw new Error('AURITE_API_KEY must be provided in production environment');
  }
  
  return {
    baseUrl,
    apiKey,
    environment,
    isDevelopment: environment === 'development',
    isTest: environment === 'test',
    isProduction: environment === 'production',
  };
}

/**
 * Global configuration instance
 * This is created once when the module is imported
 */
export const auriteConfig: AuriteConfig = createConfig();

/**
 * Get the current configuration
 * This is the recommended way to access configuration in your code
 */
export function getAuriteConfig(): AuriteConfig {
  return auriteConfig;
}

/**
 * Create a new configuration with overrides
 * Useful for testing or when you need to override specific values
 */
export function createAuriteConfig(overrides: Partial<AuriteConfig> = {}): AuriteConfig {
  return {
    ...auriteConfig,
    ...overrides,
  };
}

/**
 * Validate that the current configuration is valid
 * Throws an error if configuration is invalid
 */
export function validateConfig(config: AuriteConfig = auriteConfig): void {
  if (!config.baseUrl) {
    throw new Error('Base URL is required');
  }
  
  if (!config.baseUrl.startsWith('http://') && !config.baseUrl.startsWith('https://')) {
    throw new Error('Base URL must start with http:// or https://');
  }
  
  if (config.isProduction && !config.apiKey) {
    throw new Error('API key is required in production');
  }
}

/**
 * Get configuration for API client
 * Returns the format expected by the BaseClient
 */
export function getApiClientConfig(overrides: Partial<Pick<AuriteConfig, 'baseUrl' | 'apiKey'>> = {}) {
  const config = getAuriteConfig();
  
  return {
    baseUrl: overrides.baseUrl || config.baseUrl,
    apiKey: overrides.apiKey || config.apiKey,
  };
}

// Validate configuration on module load
validateConfig();
