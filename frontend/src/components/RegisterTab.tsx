import React, { useState } from 'react';

type ComponentType = 'clients' | 'agents' | 'workflows';

const RegisterTab: React.FC = () => {
  const [apiKey, setApiKey] = useState<string>(''); // Re-using API key input for now
  const [componentType, setComponentType] = useState<ComponentType>('clients');
  const [name, setName] = useState<string>('');
  const [config, setConfig] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    if (!apiKey) {
      setError('API Key is required to register components.');
      setIsLoading(false);
      return;
    }

    let configJson: unknown;
    try {
      configJson = JSON.parse(config || '{}'); // Default to empty object if config is empty
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (_error: unknown) { // Add eslint directive to ignore unused var
      setError('Invalid JSON in configuration.');
      setIsLoading(false);
      return;
    }

    // Construct payload based on type
    // Type check after parsing
    if (typeof configJson !== 'object' || configJson === null) {
      setError('Configuration must be a valid JSON object.');
      setIsLoading(false);
      return;
    }

    // We'll keep payload as 'any' here temporarily because its structure varies significantly
    // A more robust solution might involve defining specific types/interfaces for each component config
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let payload: any;
    if (componentType === 'clients') {
       // Now safe to access properties after type check
      const configObj = configJson as { client_id?: string }; // Type assertion for easier access
      // Client config should include client_id, use name field if not present in JSON
      if (!configObj.client_id && name) {
        configObj.client_id = name;
      } else if (!configObj.client_id && !name) {
         setError('Client Name/ID is required (either in Name field or client_id in JSON).');
         setIsLoading(false);
         return;
      }
      payload = configObj;
    } else {
      // For agents and workflows, name is required and added to the payload
      if (!name) {
        setError('Component Name is required for agents and workflows.');
        setIsLoading(false);
        return;
      }
       // Now safe to spread after type check
      payload = {
        ...(configJson as object), // Type assertion for spread
        name: name, // Ensure name from input field overrides any in JSON
      };
    }

    try {
      const response = await fetch(`/api/${componentType}/register`, { // Using proxy path
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify(payload),
      });

      const responseData = await response.json(); // Attempt to parse JSON regardless of status

      if (!response.ok) {
        const errorDetail = responseData?.detail || `Registration failed: ${response.status} ${response.statusText}`;
        throw new Error(errorDetail);
      }

      setResult(JSON.stringify(responseData, null, 2));
      // Optionally clear form on success?
      // setName('');
      // setConfig('');

    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Registration Error: ${message}`);
      setResult(null); // Clear previous success result on error
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-semibold mb-4">Register Component</h2>

      {/* API Key Input */}
      <div className="mb-4">
        <label htmlFor="apiKeyRegister" className="block text-sm font-medium text-gray-700 mb-1">
          API Key:
        </label>
        <input
          type="password"
          id="apiKeyRegister"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="Enter your API Key"
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
      </div>

      {/* Form */}
      <div className="form-group">
        <label htmlFor="componentType" className="block text-sm font-medium text-gray-700 mb-1">
          Component Type:
        </label>
        <select
          id="componentType"
          value={componentType}
          onChange={(e) => setComponentType(e.target.value as ComponentType)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        >
          <option value="clients">Client</option>
          <option value="agents">Agent</option>
          <option value="workflows">Workflow</option>
          {/* Add Custom Workflow later if needed */}
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
          Name:
        </label>
        <input
          type="text"
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Component name (required for Agent/Workflow)"
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
         <p className="mt-1 text-xs text-gray-500">For Clients, this is used as `client_id` if not present in JSON.</p>
      </div>

      <div className="form-group">
        <label htmlFor="config" className="block text-sm font-medium text-gray-700 mb-1">
          Configuration (JSON):
        </label>
        <textarea
          id="config"
          rows={10}
          value={config}
          onChange={(e) => setConfig(e.target.value)}
          placeholder="Enter JSON configuration object"
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono"
        />
      </div>

      <button
        onClick={handleRegister}
        disabled={isLoading}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? 'Registering...' : 'Register'}
      </button>

      {/* Display Area for Result/Error */}
      {/* Note: This uses the shared result display at the bottom for now */}
      {/* We might move this into the tab later */}
       {error && (
        <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          <p className="font-bold">Error:</p>
          <p>{error}</p>
        </div>
      )}
       {result && (
        <div className="mt-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
          <p className="font-bold">Success:</p>
          <pre className="text-sm overflow-x-auto">{result}</pre>
        </div>
      )}

    </div>
  );
};

export default RegisterTab;
