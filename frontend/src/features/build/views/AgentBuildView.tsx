import React, { useState, useEffect, useCallback } from 'react';
import type { AgentConfig, ProjectConfig } from '../../../types/projectManagement'; // Added ProjectConfig, Removed ClientConfig, LLMConfig
// import type { SelectedSidebarItemType } from '../../../components/layout/ComponentSidebar'; // For ExecutableItem type // Removed
import {
  saveNewConfigFile,
  listConfigFiles,
  getConfigFileContent,
  // getActiveProjectComponentConfig, // Removed
  // getSpecificComponentConfig, // Removed
  getActiveProjectFullConfig // Added
} from '../../../lib/apiClient';
// import useUIStore from '../../../store/uiStore'; // Removed
import MultiSelectModal from '../../../components/common/MultiSelectModal';

// Re-using ExecutableItem from ExecuteView for listing mcp_servers/LLMs
interface SelectableItem { // This interface is also defined in MultiSelectModal, consider moving to types if widely used
  id: string;
  displayName: string;
  type: 'mcp_servers' | 'llms'; // Specific types for this builder
  source: 'file' | 'project';
}

const AgentBuildView: React.FC = () => {
  const [agentName, setAgentName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [selectedMcpServerIds, setSelectedMcpServerIds] = useState<string[]>([]);

  const [llmConfigSource, setLlmConfigSource] = useState<'existing' | 'inline'>('existing'); // Default to 'existing'
  const [selectedLlmConfigId, setSelectedLlmConfigId] = useState<string | null>(null);
  const [inlineLlmModel, setInlineLlmModel] = useState('');
  const [inlineLlmTemperature, setInlineLlmTemperature] = useState<string>('0.7');
  const [inlineLlmMaxTokens, setInlineLlmMaxTokens] = useState<string>('2048');

  const [maxIterations, setMaxIterations] = useState<string>('10');
  // const [includeHistory, setIncludeHistory] = useState<boolean>(true); // Removed includeHistory

  const [availableMcpServers, setAvailableMcpServers] = useState<SelectableItem[]>([]);
  const [availableLlmConfigs, setAvailableLlmConfigs] = useState<SelectableItem[]>([]);
  const [isLoadingDropdowns, setIsLoadingDropdowns] = useState<boolean>(false);
  const [isMcpServerModalOpen, setIsMcpServerModalOpen] = useState<boolean>(false); // State for mcp_server modal

  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  // --- Data Fetching for Selectors ---
  const fetchSelectableItems = useCallback(async () => {
    setIsLoadingDropdowns(true); // Use dedicated loading state

    const extractNameFromFilename = (filename: string) => filename.replace(/\.json$/, '');

    const fetchAndMerge = async (
      uiType: 'mcp_servers' | 'llms',
      projectConfig: ProjectConfig | null, // Pass the full project config
      configFileApiType: "mcp_servers" | "llms"
    ): Promise<SelectableItem[]> => {
      const itemMap = new Map<string, SelectableItem>();

      // 1. File-based components
      try {
        const filenames = await listConfigFiles(configFileApiType);
        for (const fname of filenames) {
          try {
            const fileContent = await getConfigFileContent(configFileApiType, fname);
            if (Array.isArray(fileContent)) {
              fileContent.forEach((cfg: any) => {
                const id = uiType === 'mcp_servers' ? cfg.name : cfg.llm_id;
                const displayName = id || cfg.name; // Use specific ID field, fallback to name
                if (id && typeof id === 'string') {
                  itemMap.set(id, { id, displayName: displayName || id, type: uiType, source: 'file' });
                }
              });
            } else if (typeof fileContent === 'object' && fileContent !== null) {
              const id = uiType === 'mcp_servers' ? fileContent.name : fileContent.llm_id;
              const displayName = id || fileContent.name || extractNameFromFilename(fname);
              if (id && typeof id === 'string') {
                itemMap.set(id, { id, displayName, type: uiType, source: 'file' });
              } else { // Fallback for single object files if primary ID field is missing
                 const fileBasedId = extractNameFromFilename(fname);
                 itemMap.set(fileBasedId, { id: fileBasedId, displayName: fileBasedId, type: uiType, source: 'file' });
              }
            }
          } catch (e) { console.error(`Error processing file ${fname} for ${uiType}:`, e); }
        }
      } catch (e) { console.error(`Error listing config files for ${configFileApiType}:`, e); }

      // 2. Project-defined components
      if (projectConfig) {
        let namesFromProject: string[] = [];
        if (uiType === 'mcp_servers' && projectConfig.mcp_servers) {
          namesFromProject = Object.keys(projectConfig.mcp_servers);
        } else if (uiType === 'llms' && projectConfig.llms) {
          namesFromProject = Object.keys(projectConfig.llms);
        }

        namesFromProject.forEach(name => {
          if (!itemMap.has(name)) { // Add only if not already present from file-based
            itemMap.set(name, { id: name, displayName: name, type: uiType, source: 'project' });
          }
        });
      }
      return Array.from(itemMap.values()).sort((a,b) => a.displayName.localeCompare(b.displayName));
    };

    try {
        const activeProjectConfig = await getActiveProjectFullConfig();
        setAvailableMcpServers(await fetchAndMerge('mcp_servers', activeProjectConfig, 'mcp_servers'));
        setAvailableLlmConfigs(await fetchAndMerge('llms', activeProjectConfig, 'llms'));
    } catch(err) {
        console.error("Error fetching items for agent builder selectors:", err);
        // Set an error state for selectors if needed, e.g. setErrorForDropdowns(true)
    } finally {
        setIsLoadingDropdowns(false);
    }
  }, []);

  useEffect(() => {
    fetchSelectableItems();
  }, [fetchSelectableItems]);


  const handleSaveAgent = async () => {
    if (!agentName.trim()) {
      setSaveError("Agent Name is required.");
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    const configToSave: Partial<AgentConfig> = {
      name: agentName.trim(),
      system_prompt: systemPrompt.trim() || undefined,
      mcp_servers: selectedMcpServerIds.length > 0 ? selectedMcpServerIds : undefined,
      max_iterations: maxIterations ? parseInt(maxIterations) : undefined,
    };

    if (llmConfigSource === 'existing' && selectedLlmConfigId) {
      configToSave.llm_config_id = selectedLlmConfigId;
      // Clear inline params if existing is chosen
      delete configToSave.model;
      delete configToSave.temperature;
      delete configToSave.max_tokens;
    } else if (llmConfigSource === 'inline') {
      if (inlineLlmModel.trim()) configToSave.model = inlineLlmModel.trim();
      // Only add temp/tokens if model is also specified for inline
      if (inlineLlmModel.trim() && inlineLlmTemperature.trim()) configToSave.temperature = parseFloat(inlineLlmTemperature);
      if (inlineLlmModel.trim() && inlineLlmMaxTokens.trim()) configToSave.max_tokens = parseInt(inlineLlmMaxTokens);
      // Ensure llm_config_id is not set if inline is chosen
      delete configToSave.llm_config_id;
    } else {
      // This case should ideally not be reached if UI only allows 'existing' or 'inline'
      // but as a fallback, ensure no LLM params are set.
      delete configToSave.llm_config_id;
      delete configToSave.model;
      delete configToSave.temperature;
      delete configToSave.max_tokens;
    }

    // Remove undefined fields for cleaner JSON
    Object.keys(configToSave).forEach(key => (configToSave as any)[key] === undefined && delete (configToSave as any)[key]);

    const filename = agentName.trim().replace(/\s+/g, '_') + ".json";

    try {
      await saveNewConfigFile("agents", filename, configToSave);
      setSaveSuccess(`Agent "${agentName}" saved successfully as ${filename}.`);
      // Optionally reset form here
    } catch (err) {
      const apiError = err as any;
      console.error("Failed to save agent config:", err);
      setSaveError(apiError.message || `Failed to save agent ${filename}.`);
    } finally {
      setIsSaving(false);
    }
  };

  // TODO: Implement UI for client selection (modal/multiselect dropdown)
  // TODO: Implement UI for LLM config selection (dropdown for existing, fields for inline)

  return (
    <div className="p-4 space-y-6 max-w-3xl mx-auto">
      <h2 className="text-2xl font-semibold text-dracula-pink">Build New Agent</h2>

      <div className="p-6 bg-dracula-current-line rounded-lg shadow-md space-y-4">
        <div>
          <label htmlFor="agentName" className="block text-sm font-medium text-dracula-foreground mb-1">Agent Name</label>
          <input
            type="text"
            id="agentName"
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            placeholder="e.g., Customer Support Agent"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>

        <div>
          <label htmlFor="systemPrompt" className="block text-sm font-medium text-dracula-foreground mb-1">System Prompt</label>
          <textarea
            id="systemPrompt"
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows={4}
            placeholder="e.g., You are a helpful assistant..."
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>
      </div>

      {/* MCP Server Selection Section */}
      <div className="p-6 bg-dracula-current-line rounded-lg shadow-md space-y-4">
        <h3 className="text-lg font-semibold text-dracula-cyan">MCP Servers</h3>
        <div className="mb-2">
          {selectedMcpServerIds.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {selectedMcpServerIds.map(mcpServerId => (
                <span key={mcpServerId} className="px-2 py-1 bg-dracula-purple text-dracula-background text-xs rounded-full">
                  {mcpServerId}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-dracula-comment text-xs">None selected.</p>
          )}
        </div>
        <button
          onClick={() => setIsMcpServerModalOpen(true)}
          className="px-4 py-2 text-sm font-medium text-dracula-background bg-dracula-cyan hover:bg-opacity-80 rounded-md focus:outline-none focus:ring-2 focus:ring-dracula-pink"
          disabled={isLoadingDropdowns} // Disable if mcp_servers are still loading
        >
          {isLoadingDropdowns && availableMcpServers.length === 0 ? 'Loading MCP Servers...' : 'Select MCP Servers'}
        </button>
        {availableMcpServers.length === 0 && !isLoadingDropdowns && <p className="text-xs text-dracula-comment mt-1">No MCP Servers available to select.</p>}
      </div>

      <MultiSelectModal
        isOpen={isMcpServerModalOpen}
        onClose={() => setIsMcpServerModalOpen(false)}
        title="Select MCP Servers"
        items={availableMcpServers.map(server => ({ id: server.id, displayName: server.displayName }))} // Adapt SelectableItem for modal
        selectedIds={selectedMcpServerIds}
        onConfirmSelection={(newMcpServerIds) => setSelectedMcpServerIds(newMcpServerIds)}
      />

      {/* LLM Configuration Section */}
      <div className="p-6 bg-dracula-current-line rounded-lg shadow-md space-y-4">
        <h3 className="text-lg font-semibold text-dracula-cyan">LLM Configuration</h3>
        <div className="space-y-2">
          {(['existing', 'inline'] as const).map(source => ( // Removed 'none'
            <div key={source} className="flex items-center">
              <input
                type="radio"
                id={`llmSource-${source}`}
                name="llmConfigSource"
                value={source}
                checked={llmConfigSource === source}
                onChange={(e) => {
                  const newSource = e.target.value as 'existing' | 'inline';
                  setLlmConfigSource(newSource);
                  if (newSource === 'existing') {
                    setInlineLlmModel('');
                    setInlineLlmTemperature('0.7');
                    setInlineLlmMaxTokens('2048');
                  } else { // 'inline'
                    setSelectedLlmConfigId(null);
                  }
                }}
                className="h-4 w-4 text-dracula-pink border-dracula-comment focus:ring-dracula-pink"
              />
              <label htmlFor={`llmSource-${source}`} className="ml-2 text-sm text-dracula-foreground">
                {source === 'existing' ? 'Use Existing LLM Config' : 'Define Inline LLM Parameters'}
              </label>
            </div>
          ))}
        </div>

        {llmConfigSource === 'existing' && (
          <div className="mt-4 space-y-2">
            <label htmlFor="selectedLlmConfigId" className="block text-sm font-medium text-dracula-foreground mb-1">Select LLM Config</label>
            <select
              id="selectedLlmConfigId"
              value={selectedLlmConfigId || ''}
              onChange={(e) => setSelectedLlmConfigId(e.target.value || null)}
              className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
              disabled={availableLlmConfigs.length === 0}
            >
              <option value="">-- Select LLM Config --</option>
              {availableLlmConfigs.map(llm => (
                <option key={llm.id} value={llm.id}>{llm.displayName}</option>
              ))}
            </select>
            {availableLlmConfigs.length === 0 && !isLoadingDropdowns && <p className="text-xs text-dracula-comment mt-1">No LLM configs available to select.</p>}
          </div>
        )}

        {llmConfigSource === 'inline' && (
          <div className="mt-4 space-y-4">
            <div>
              <label htmlFor="inlineLlmModel" className="block text-sm font-medium text-dracula-foreground mb-1">Model Name</label>
              <input type="text" id="inlineLlmModel" value={inlineLlmModel} onChange={(e) => setInlineLlmModel(e.target.value)} placeholder="e.g., gpt-4-turbo" className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground" />
            </div>
            <div>
              <label htmlFor="inlineLlmTemperature" className="block text-sm font-medium text-dracula-foreground mb-1">Temperature</label>
              <input type="number" step="0.1" id="inlineLlmTemperature" value={inlineLlmTemperature} onChange={(e) => setInlineLlmTemperature(e.target.value)} placeholder="0.0 to 2.0" className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground" />
            </div>
            <div>
              <label htmlFor="inlineLlmMaxTokens" className="block text-sm font-medium text-dracula-foreground mb-1">Max Tokens</label>
              <input type="number" id="inlineLlmMaxTokens" value={inlineLlmMaxTokens} onChange={(e) => setInlineLlmMaxTokens(e.target.value)} placeholder="e.g., 2048" className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground" />
            </div>
          </div>
        )}
      </div>

      {/* Other Agent Params */}
       <div className="p-6 bg-dracula-current-line rounded-lg shadow-md space-y-4">
        <h3 className="text-lg font-semibold text-dracula-cyan">Other Parameters</h3>
         <div>
            <label htmlFor="maxIterations" className="block text-sm font-medium text-dracula-foreground mb-1">Max Iterations</label>
            <input type="number" id="maxIterations" value={maxIterations} onChange={(e) => setMaxIterations(e.target.value)} className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground" />
        </div>
        {/* <div className="flex items-center">
            <input type="checkbox" id="includeHistory" checked={includeHistory} onChange={(e) => setIncludeHistory(e.target.checked)} className="h-4 w-4 text-dracula-pink bg-dracula-background border-dracula-comment rounded focus:ring-dracula-pink" />
            <label htmlFor="includeHistory" className="ml-2 block text-sm text-dracula-foreground">Include History</label>
        </div> */}
      </div>


      <div className="flex justify-end items-center space-x-3 mt-6">
        {saveError && <p className="text-sm text-dracula-red">{saveError}</p>}
        {saveSuccess && <p className="text-sm text-dracula-green">{saveSuccess}</p>}
        <button
          onClick={handleSaveAgent}
          disabled={isSaving || !agentName.trim()}
          className="px-6 py-2 bg-dracula-green text-dracula-background font-semibold rounded-md hover:bg-opacity-90 focus:outline-none focus:ring-2 focus:ring-dracula-pink disabled:bg-dracula-comment disabled:cursor-not-allowed"
        >
          {isSaving ? 'Saving...' : 'Save Agent Config'}
        </button>
      </div>
    </div>
  );
};

// Dummy/placeholder for missing API functions until they are added to apiClient.ts
// Removed local mock functions as they are no longer used by fetchAndMerge

export default AgentBuildView;
