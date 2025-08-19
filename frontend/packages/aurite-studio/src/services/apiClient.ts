import { AuriteApiClient } from '@aurite-ai/api-client';

// Extend Window interface to include AURITE_CONFIG
declare global {
  interface Window {
    AURITE_CONFIG?: {
      apiKey: string;
      apiBaseUrl: string;
      serverPort: string;
      environment: string;
      version: string;
    };
  }
}

// Get configuration from server-injected config or fallback to environment variables
function getApiConfiguration() {
  // Check if we have server-injected configuration (production/static mode)
  // Only use it if the values are actually processed (not template placeholders)
  if (typeof window !== 'undefined' && window.AURITE_CONFIG) {
    const config = window.AURITE_CONFIG;
    
    // Check if the config values are processed (not template placeholders)
    const isProcessed = config.apiBaseUrl && 
                       !config.apiBaseUrl.includes('{{') && 
                       !config.apiBaseUrl.includes('}}');
    
    if (isProcessed) {
      return {
        baseUrl: config.apiBaseUrl || `http://localhost:${config.serverPort || '8000'}`,
        apiKey: config.apiKey || ''
      };
    }
  }
  
  // Fallback to environment variables (development mode)
  return {
    baseUrl: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
    apiKey: process.env.REACT_APP_API_KEY || ''
  };
}

// Create and configure the API client with dynamic configuration
const config = getApiConfiguration();
const apiClient = new AuriteApiClient(config);

export default apiClient;
