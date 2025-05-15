import React, { useState } from 'react';
import type { LLMConfig } from '../../../types/projectManagement';
import { saveNewConfigFile } from '../../../lib/apiClient';

const LLMBuildView: React.FC = () => {
  const [llmId, setLlmId] = useState('');
  const [provider, setProvider] = useState('');
  const [modelName, setModelName] = useState('');
  const [temperatureInput, setTemperatureInput] = useState(''); // Default e.g. '0.7'
  const [maxTokensInput, setMaxTokensInput] = useState('');   // Default e.g. '2048'
  const [defaultSystemPrompt, setDefaultSystemPrompt] = useState('');

  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const handleSaveLlmConfig = async () => {
    if (!llmId.trim()) {
      setSaveError("LLM ID is required.");
      return;
    }
    // Provider and Model Name are highly recommended for a functional config
    if (!provider.trim()) {
        setSaveError("Provider is highly recommended.");
        // return; // Or allow saving without it
    }
    if (!modelName.trim()) {
        setSaveError("Model Name is highly recommended.");
        // return; // Or allow saving without it
    }


    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    const configToSave: Partial<LLMConfig> = {
      llm_id: llmId.trim(),
    };

    if (provider.trim()) configToSave.provider = provider.trim();
    if (modelName.trim()) configToSave.model_name = modelName.trim();
    if (temperatureInput.trim()) {
      const tempVal = parseFloat(temperatureInput);
      if (!isNaN(tempVal)) configToSave.temperature = tempVal;
    }
    if (maxTokensInput.trim()) {
      const tokensVal = parseInt(maxTokensInput, 10);
      if (!isNaN(tokensVal)) configToSave.max_tokens = tokensVal;
    }
    if (defaultSystemPrompt.trim()) configToSave.default_system_prompt = defaultSystemPrompt.trim();

    const filename = llmId.trim().replace(/\s+/g, '_') + ".json";

    try {
      await saveNewConfigFile("llms", filename, configToSave);
      setSaveSuccess(`LLM Config "${llmId}" saved successfully as ${filename}.`);
      // Optionally reset form
      // setLlmId('');
      // setProvider('');
      // setModelName('');
      // setTemperatureInput('');
      // setMaxTokensInput('');
      // setDefaultSystemPrompt('');
    } catch (err) {
      const apiError = err as any;
      console.error("Failed to save LLM config:", err);
      setSaveError(apiError.message || `Failed to save LLM config ${filename}.`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-4 space-y-6 max-w-3xl mx-auto">
      <h2 className="text-2xl font-semibold text-dracula-pink">Build New LLM Configuration</h2>

      <div className="p-6 bg-dracula-current-line rounded-lg shadow-md space-y-4">
        <div>
          <label htmlFor="llmId" className="block text-sm font-medium text-dracula-foreground mb-1">LLM ID</label>
          <input
            type="text"
            id="llmId"
            value={llmId}
            onChange={(e) => setLlmId(e.target.value)}
            placeholder="e.g., my_claude_opus_config"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>

        <div>
          <label htmlFor="provider" className="block text-sm font-medium text-dracula-foreground mb-1">Provider (Optional)</label>
          <input
            type="text"
            id="provider"
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            placeholder="e.g., anthropic, openai, google"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>

        <div>
          <label htmlFor="modelName" className="block text-sm font-medium text-dracula-foreground mb-1">Model Name (Optional)</label>
          <input
            type="text"
            id="modelName"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            placeholder="e.g., claude-3-opus-20240229, gpt-4-turbo"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>

        <div>
          <label htmlFor="temperatureInput" className="block text-sm font-medium text-dracula-foreground mb-1">Temperature (Optional)</label>
          <input
            type="number"
            step="0.1"
            id="temperatureInput"
            value={temperatureInput}
            onChange={(e) => setTemperatureInput(e.target.value)}
            placeholder="e.g., 0.7 (0.0 to 2.0)"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>

        <div>
          <label htmlFor="maxTokensInput" className="block text-sm font-medium text-dracula-foreground mb-1">Max Tokens (Optional)</label>
          <input
            type="number"
            id="maxTokensInput"
            value={maxTokensInput}
            onChange={(e) => setMaxTokensInput(e.target.value)}
            placeholder="e.g., 2048"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>

        <div>
          <label htmlFor="defaultSystemPrompt" className="block text-sm font-medium text-dracula-foreground mb-1">Default System Prompt (Optional)</label>
          <textarea
            id="defaultSystemPrompt"
            value={defaultSystemPrompt}
            onChange={(e) => setDefaultSystemPrompt(e.target.value)}
            rows={3}
            placeholder="Enter a default system prompt for this LLM configuration."
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>
      </div>

      <div className="flex justify-end items-center space-x-3 mt-6">
        {saveError && <p className="text-sm text-dracula-red">{saveError}</p>}
        {saveSuccess && <p className="text-sm text-dracula-green">{saveSuccess}</p>}
        <button
          onClick={handleSaveLlmConfig}
          disabled={isSaving || !llmId.trim()}
          className="px-6 py-2 bg-dracula-green text-dracula-background font-semibold rounded-md hover:bg-opacity-90 focus:outline-none focus:ring-2 focus:ring-dracula-pink disabled:bg-dracula-comment disabled:cursor-not-allowed"
        >
          {isSaving ? 'Saving...' : 'Save LLM Config'}
        </button>
      </div>
    </div>
  );
};

export default LLMBuildView;
