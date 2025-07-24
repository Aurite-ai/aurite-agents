/**
 * Aurite API Client for TypeScript/JavaScript
 *
 * A comprehensive client library for interacting with the Aurite Framework API.
 *
 * @packageDocumentation
 */

// Main exports
export {
  AuriteApiClient,
  createAuriteClient,
  createAuriteClientFromEnv,
} from './client/AuriteApiClient';

// Sub-client exports (for advanced usage)
export { ExecutionFacadeClient } from './routes/ExecutionFacadeClient';
export { MCPHostClient } from './routes/MCPHostClient';
export { ConfigManagerClient } from './routes/ConfigManagerClient';
export { BaseClient } from './client/BaseClient';

// Type exports
export * from './types';

// Environment configuration exports
export * from './config/browser-environment';
