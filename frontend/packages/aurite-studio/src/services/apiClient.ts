import { AuriteApiClient } from '@aurite/api-client';

// Create and configure the API client manually to avoid Node.js dependencies
const apiClient = new AuriteApiClient({
  baseUrl: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
  apiKey: process.env.REACT_APP_API_KEY || ''
});

export default apiClient;
