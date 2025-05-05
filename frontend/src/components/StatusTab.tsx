import React, { useState } from 'react';

const StatusTab: React.FC = () => {
  const [apiKey, setApiKey] = useState<string>('');
  const [healthStatus, setHealthStatus] = useState<string | null>(null);
  const [systemStatus, setSystemStatus] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const checkStatus = async () => {
    setIsLoading(true);
    setError(null);
    setHealthStatus(null);
    setSystemStatus(null);

    // --- Fetch Health Status (No API Key needed) ---
    try {
      const healthResponse = await fetch('/api/health'); // Using proxy path
      if (!healthResponse.ok) {
        throw new Error(`Health check failed: ${healthResponse.status} ${healthResponse.statusText}`);
      }
      const healthData = await healthResponse.json();
      setHealthStatus(JSON.stringify(healthData, null, 2));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Health Check Error: ${message}`);
      setHealthStatus('Error fetching health status.');
      // Don't proceed to system status if health check fails fundamentally
      setIsLoading(false);
      return;
    }

    // --- Fetch System Status (API Key needed) ---
    if (!apiKey) {
      setError('API Key is required to check system status.');
      setSystemStatus('API Key required.');
      setIsLoading(false);
      return;
    }

    try {
      const statusResponse = await fetch('/api/status', { // Using proxy path
        headers: {
          'X-API-Key': apiKey,
        },
      });

      const statusData = await statusResponse.json(); // Attempt to parse JSON regardless of status

      if (!statusResponse.ok) {
         // Use error detail from API response if available
        const errorDetail = statusData?.detail || `System status check failed: ${statusResponse.status} ${statusResponse.statusText}`;
        throw new Error(errorDetail);
      }

      setSystemStatus(JSON.stringify(statusData, null, 2));

    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`System Status Error: ${message}`);
      setSystemStatus('Error fetching system status.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-semibold mb-4">System Status</h2>

      {/* API Key Input */}
      <div className="mb-4">
        <label htmlFor="apiKeyStatus" className="block text-sm font-medium text-gray-700 mb-1">
          API Key:
        </label>
        <input
          type="password" // Use password type for basic masking
          id="apiKeyStatus"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="Enter your API Key"
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
         <p className="mt-1 text-xs text-gray-500">Required for System Status check.</p>
      </div>

      <button
        onClick={checkStatus}
        disabled={isLoading}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? 'Checking...' : 'Check Status'}
      </button>

      {error && (
        <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          <p className="font-bold">Error:</p>
          <p>{error}</p>
        </div>
      )}

      <div className="status-info mt-6 space-y-4">
        <div>
          <h3 className="text-lg font-medium mb-2">Health Check Result</h3>
          <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto min-h-[50px]">
            {healthStatus ?? 'Not checked yet.'}
          </pre>
        </div>

        <div>
          <h3 className="text-lg font-medium mb-2">System Status Result</h3>
           <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto min-h-[50px]">
            {systemStatus ?? 'Not checked yet.'}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default StatusTab;
