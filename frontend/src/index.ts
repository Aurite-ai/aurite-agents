/**
 * Aurite API Client for TypeScript/JavaScript
 *
 * A comprehensive client library for interacting with the Aurite Framework API.
 *
 * @packageDocumentation
 */

// Main exports
export { AuriteApiClient, createAuriteClient } from './AuriteApiClient';

// Sub-client exports (for advanced usage)
export { ExecutionFacadeClient } from './routes/ExecutionFacadeClient';
export { MCPHostClient } from './routes/MCPHostClient';
export { ConfigManagerClient } from './routes/ConfigManagerClient';
export { BaseClient } from './BaseClient';

// Type exports
export * from './types';
