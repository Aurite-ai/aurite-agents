/**
 * Browser-compatible environment configuration for the Aurite API Client
 * This module provides configuration without Node.js dependencies
 */

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
  // In browser environments, we can't access process.env directly
  // This will be handled by the build system (webpack, vite, etc.)
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
        baseUrl: 'https://api.aurite.ai', // Example production URL
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
  const apiKey = getEnvVar('API_KEY', defaults.apiKey, environment === 'production');

  // Validate required fields
  if (!baseUrl) {
    throw new Error('AURITE_API_BASE_URL must be provided');
  }

  if (environment === 'production' && !apiKey) {
    throw new Error('API_KEY must be provided in production environment');
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
 * Get configuration for API client
 * Returns the format expected by the BaseClient
 */
export function getApiClientConfig(
  overrides: Partial<Pick<AuriteConfig, 'baseUrl' | 'apiKey'>> = {}
) {
  const config = createConfig();

  return {
    baseUrl: overrides.baseUrl || config.baseUrl,
    apiKey: overrides.apiKey || config.apiKey,
  };
}

/**
 * Create a new configuration with overrides
 * Useful for testing or when you need to override specific values
 */
export function createAuriteConfig(overrides: Partial<AuriteConfig> = {}): AuriteConfig {
  const config = createConfig();
  return {
    ...lib.config,
    ...overrides,
  };
}
