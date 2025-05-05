import React, { useState, useEffect } from 'react';

type ExecComponentType = 'agents' | 'workflows' | 'custom_workflows';

const ExecuteTab: React.FC = () => {
  const [apiKey, setApiKey] = useState<string>(''); // Re-using API key input
  const [componentType, setComponentType] = useState<ExecComponentType>('agents');
  const [name, setName] = useState<string>('');
  const [inputJsonStr, setInputJsonStr] = useState<string>('{}'); // Store input as string
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // State to control visibility of system prompt field
  const [showSystemPrompt, setShowSystemPrompt] = useState<boolean>(componentType === 'agents');

  // Update system prompt visibility when component type changes
  useEffect(() => {
    setShowSystemPrompt(componentType === 'agents');
  }, [componentType]);

  const handleExecute = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    if (!apiKey) {
      setError('API Key is required to execute components.');
      setIsLoading(false);
      return;
    }

    if (!name) {
      setError('Component Name is required.');
      setIsLoading(false);
      return;
    }

    let inputJson: unknown;
    try {
      inputJson = JSON.parse(inputJsonStr || '{}'); // Parse input string
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (_error: unknown) { // Ignore unused var
      setError('Invalid JSON in input field.');
      setIsLoading(false);
      return;
    }

    // Type check after parsing
    if (typeof inputJson !== 'object' || inputJson === null) {
        setError('Input must be a valid JSON object.');
        setIsLoading(false);
        return;
    }

    // Prepare URL and payload based on component type
    let url: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let payload: any; // Allow 'any' for payload temporarily

    if (componentType === 'agents') {
      url = `/api/agents/${name}/execute`;
      // Now safe to access properties after type check
      const inputObj = inputJson as { user_message?: string, system_prompt?: string };
      // Use dedicated system prompt field if filled, otherwise check JSON input (optional)
      const finalSystemPrompt = systemPrompt.trim() || inputObj.system_prompt || null;
      payload = {
        user_message: inputObj.user_message || '', // Ensure user_message exists
        system_prompt: finalSystemPrompt,
      };
    } else if (componentType === 'workflows') {
      url = `/api/workflows/${name}/execute`;
      const inputObj = inputJson as { initial_user_message?: string };
      payload = { initial_user_message: inputObj.initial_user_message || '' };
    } else if (componentType === 'custom_workflows') {
      url = `/api/custom_workflows/${name}/execute`;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const inputObj = inputJson as { initial_input?: any }; // Keep initial_input flexible
      payload = { initial_input: inputObj.initial_input || {} };
    } else {
      setError('Invalid component type selected.');
      setIsLoading(false);
      return; // Should not happen with select dropdown
    }

    try {
      const response = await fetch(url, { // Using proxy path
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify(payload),
      });

      const responseData = await response.json(); // Attempt to parse JSON regardless of status

      if (!response.ok) {
        const errorDetail = responseData?.detail || `Execution failed: ${response.status} ${response.statusText}`;
        throw new Error(errorDetail);
      }

      setResult(JSON.stringify(responseData, null, 2));

    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Execution Error: ${message}`);
      setResult(null); // Clear previous success result on error
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-semibold mb-4">Execute Component</h2>

      {/* API Key Input */}
      <div className="mb-4">
        <label htmlFor="apiKeyExecute" className="block text-sm font-medium text-gray-700 mb-1">
          API Key:
        </label>
        <input
          type="password"
          id="apiKeyExecute"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="Enter your API Key"
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
      </div>

      {/* Form */}
      <div className="form-group">
        <label htmlFor="execComponentType" className="block text-sm font-medium text-gray-700 mb-1">
          Component Type:
        </label>
        <select
          id="execComponentType"
          value={componentType}
          onChange={(e) => setComponentType(e.target.value as ExecComponentType)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        >
          <option value="agents">Agent</option>
          <option value="workflows">Workflow</option>
          <option value="custom_workflows">Custom Workflow</option>
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="execName" className="block text-sm font-medium text-gray-700 mb-1">
          Name:
        </label>
        <input
          type="text"
          id="execName"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Component name"
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
      </div>

      <div className="form-group">
        <label htmlFor="inputJson" className="block text-sm font-medium text-gray-700 mb-1">
          Input (JSON):
        </label>
        <textarea
          id="inputJson"
          rows={8}
          value={inputJsonStr}
          onChange={(e) => setInputJsonStr(e.target.value)}
          placeholder='Enter JSON input object, e.g., {"user_message": "Hello"}'
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono"
        />
        <div className="mt-1 text-xs text-gray-500 space-y-1">
          <p>Agents: Requires `user_message`. Optional `system_prompt` (can also use field below).</p>
          <p>Workflows: Requires `initial_user_message`.</p>
          <p>Custom Workflows: Requires `initial_input`.</p>
        </div>
      </div>

      {/* Conditional System Prompt for Agents */}
      {showSystemPrompt && (
        <div className="form-group">
          <label htmlFor="systemPrompt" className="block text-sm font-medium text-gray-700 mb-1">
            System Prompt (Optional Override):
          </label>
          <textarea
            id="systemPrompt"
            rows={4}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="Leave empty to use agent's default system prompt"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          />
        </div>
      )}

      <button
        onClick={handleExecute}
        disabled={isLoading || !name} // Also disable if name is empty
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? 'Executing...' : 'Execute'}
      </button>

      {/* Display Area for Result/Error */}
       {error && (
        <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          <p className="font-bold">Error:</p>
          <p>{error}</p>
        </div>
      )}
       {result && (
        <div className="mt-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
          <p className="font-bold">Result:</p>
          <pre className="text-sm overflow-x-auto">{result}</pre>
        </div>
      )}

    </div>
  );
};

export default ExecuteTab;
