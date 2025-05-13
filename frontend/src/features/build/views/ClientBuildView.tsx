import React, { useState } from 'react';
import type { ClientConfig } from '../../../types/projectManagement';
import { saveNewConfigFile } from '../../../lib/apiClient';

const ClientBuildView: React.FC = () => {
  const [clientId, setClientId] = useState('');
  const [serverPath, setServerPath] = useState('');
  const [capabilitiesInput, setCapabilitiesInput] = useState(''); // Comma-separated
  const [timeoutInput, setTimeoutInput] = useState('');
  const [routingWeightInput, setRoutingWeightInput] = useState('');

  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const handleSaveClient = async () => {
    if (!clientId.trim()) {
      setSaveError("Client ID is required.");
      return;
    }
    if (!serverPath.trim()) {
      setSaveError("Server Path is required.");
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    const capabilitiesArray = capabilitiesInput.split(',').map(s => s.trim()).filter(s => s.length > 0);

    const configToSave: Partial<ClientConfig> = {
      client_id: clientId.trim(),
      server_path: serverPath.trim(),
      roots: [], // Default to empty array as per schema, not handled by simple UI yet
    };

    if (capabilitiesArray.length > 0) {
      configToSave.capabilities = capabilitiesArray;
    }
    if (timeoutInput.trim()) {
      const timeoutVal = parseFloat(timeoutInput);
      if (!isNaN(timeoutVal)) configToSave.timeout = timeoutVal;
    }
    if (routingWeightInput.trim()) {
      const weightVal = parseFloat(routingWeightInput);
      if (!isNaN(weightVal)) configToSave.routing_weight = weightVal;
    }

    // Remove undefined fields for cleaner JSON (though not strictly necessary as Partial allows undefined)
    // Object.keys(configToSave).forEach(key => (configToSave as any)[key] === undefined && delete (configToSave as any)[key]);


    const filename = clientId.trim().replace(/\s+/g, '_') + ".json";

    try {
      await saveNewConfigFile("clients", filename, configToSave);
      setSaveSuccess(`Client "${clientId}" saved successfully as ${filename}.`);
      // Optionally reset form
      // setClientId('');
      // setServerPath('');
      // setCapabilitiesInput('');
      // setTimeoutInput('');
      // setRoutingWeightInput('');
    } catch (err) {
      const apiError = err as any;
      console.error("Failed to save client config:", err);
      setSaveError(apiError.message || `Failed to save client ${filename}.`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-4 space-y-6 max-w-3xl mx-auto">
      <h2 className="text-2xl font-semibold text-dracula-pink">Build New Client</h2>

      <div className="p-6 bg-dracula-current-line rounded-lg shadow-md space-y-4">
        <div>
          <label htmlFor="clientId" className="block text-sm font-medium text-dracula-foreground mb-1">Client ID</label>
          <input
            type="text"
            id="clientId"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            placeholder="e.g., my_custom_client"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>

        <div>
          <label htmlFor="serverPath" className="block text-sm font-medium text-dracula-foreground mb-1">Server Path</label>
          <input
            type="text"
            id="serverPath"
            value={serverPath}
            onChange={(e) => setServerPath(e.target.value)}
            placeholder="e.g., src/packaged_servers/my_server.py"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>

        <div>
          <label htmlFor="capabilitiesInput" className="block text-sm font-medium text-dracula-foreground mb-1">Capabilities (comma-separated)</label>
          <input
            type="text"
            id="capabilitiesInput"
            value={capabilitiesInput}
            onChange={(e) => setCapabilitiesInput(e.target.value)}
            placeholder="e.g., tools, prompts, resources"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>

        <div>
          <label htmlFor="timeoutInput" className="block text-sm font-medium text-dracula-foreground mb-1">Timeout (seconds, optional)</label>
          <input
            type="number"
            id="timeoutInput"
            value={timeoutInput}
            onChange={(e) => setTimeoutInput(e.target.value)}
            placeholder="e.g., 15"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>

        <div>
          <label htmlFor="routingWeightInput" className="block text-sm font-medium text-dracula-foreground mb-1">Routing Weight (optional)</label>
          <input
            type="number"
            step="0.1"
            id="routingWeightInput"
            value={routingWeightInput}
            onChange={(e) => setRoutingWeightInput(e.target.value)}
            placeholder="e.g., 1.0"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>
      </div>

      <div className="flex justify-end items-center space-x-3 mt-6">
        {saveError && <p className="text-sm text-dracula-red">{saveError}</p>}
        {saveSuccess && <p className="text-sm text-dracula-green">{saveSuccess}</p>}
        <button
          onClick={handleSaveClient}
          disabled={isSaving || !clientId.trim() || !serverPath.trim()}
          className="px-6 py-2 bg-dracula-green text-dracula-background font-semibold rounded-md hover:bg-opacity-90 focus:outline-none focus:ring-2 focus:ring-dracula-pink disabled:bg-dracula-comment disabled:cursor-not-allowed"
        >
          {isSaving ? 'Saving...' : 'Save Client Config'}
        </button>
      </div>
    </div>
  );
};

export default ClientBuildView;
