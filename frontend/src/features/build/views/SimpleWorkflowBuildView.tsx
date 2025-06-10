import React, { useState, useEffect, useCallback } from 'react';
import type { WorkflowConfig, AgentConfig } from '../../../types/projectManagement'; // Removed ProjectConfig
import {
  saveNewConfigFile,
  listConfigFiles,
  getConfigFileContent,
  getActiveProjectFullConfig,
} from '../../../lib/apiClient';

// Using a similar SelectableItem structure for agents
interface SelectableAgentItem {
  id: string; // Agent name/ID
  displayName: string;
  source: 'file' | 'project';
}

const SimpleWorkflowBuildView: React.FC = () => {
  const [workflowName, setWorkflowName] = useState('');
  const [description, setDescription] = useState('');
  const [steps, setSteps] = useState<string[]>([]); // Array of agent names/IDs

  const [availableAgents, setAvailableAgents] = useState<SelectableAgentItem[]>([]);
  const [isLoadingAgents, setIsLoadingAgents] = useState<boolean>(false);
  const [agentToAdd, setAgentToAdd] = useState<string>(''); // State for the dropdown selection

  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const fetchAvailableAgents = useCallback(async () => {
    setIsLoadingAgents(true);
    const itemMap = new Map<string, SelectableAgentItem>();
    // const extractNameFromFilename = (filename: string) => filename.replace(/\.json$/, ''); // Removed unused const

    // 1. File-based agents
    try {
      const filenames = await listConfigFiles("agents");
      for (const fname of filenames) {
        try {
          const fileContent = await getConfigFileContent("agents", fname);
          if (Array.isArray(fileContent)) {
            fileContent.forEach((cfg: AgentConfig) => {
              if (cfg.name && typeof cfg.name === 'string') {
                itemMap.set(cfg.name, { id: cfg.name, displayName: cfg.name, source: 'file' });
              }
            });
          } else if (typeof fileContent === 'object' && fileContent !== null && (fileContent as AgentConfig).name) {
            const agentCfg = fileContent as AgentConfig;
            if (agentCfg.name && typeof agentCfg.name === 'string') {
              itemMap.set(agentCfg.name, { id: agentCfg.name, displayName: agentCfg.name, source: 'file' });
            }
          }
        } catch (e) { console.error(`Error processing agent file ${fname}:`, e); }
      }
    } catch (e) { console.error(`Error listing agent config files:`, e); }

    // 2. Project-defined agents
    try {
      const projectConfig = await getActiveProjectFullConfig();
      if (projectConfig && projectConfig.agents) {
        Object.values(projectConfig.agents).forEach((agentCfg: AgentConfig) => {
          if (agentCfg.name && !itemMap.has(agentCfg.name)) {
            itemMap.set(agentCfg.name, { id: agentCfg.name, displayName: agentCfg.name, source: 'project' });
          }
        });
      }
    } catch (e) { console.error(`Error fetching agents from project config:`, e); }

    setAvailableAgents(Array.from(itemMap.values()).sort((a, b) => a.displayName.localeCompare(b.displayName)));
    setIsLoadingAgents(false);
  }, []);

  useEffect(() => {
    fetchAvailableAgents();
  }, [fetchAvailableAgents]);

  useEffect(() => {
    // Set a default for the dropdown once agents are loaded
    if (availableAgents.length > 0 && !agentToAdd) {
      setAgentToAdd(availableAgents[0].id);
    }
  }, [availableAgents]); // This effect runs only when availableAgents array changes

  const handleAddStep = () => {
    if (agentToAdd) {
      setSteps(prevSteps => [...prevSteps, agentToAdd]);
    }
  };

  const handleRemoveStep = (indexToRemove: number) => {
    setSteps(prevSteps => prevSteps.filter((_, index) => index !== indexToRemove));
  };

  const handleSaveWorkflow = async () => {
    if (!workflowName.trim()) {
      setSaveError("Workflow Name is required.");
      return;
    }
    if (steps.length === 0) {
      setSaveError("Workflow must have at least one step.");
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    const configToSave: Partial<WorkflowConfig> = {
      name: workflowName.trim(),
      steps: steps,
      description: description.trim() || undefined,
    };

    Object.keys(configToSave).forEach(key => (configToSave as any)[key] === undefined && delete (configToSave as any)[key]);

    const filename = workflowName.trim().replace(/\s+/g, '_') + ".json";

    try {
      // Note: apiClient's listConfigFiles maps "simple_workflows" to "simple-workflows" path.
      // Ensure saveNewConfigFile also uses "simple-workflows" if that's the backend expectation for the path.
      // Based on backend API_TO_CM_TYPE_MAP, "simple-workflows" is the key for the /configs/ path.
      await saveNewConfigFile("simple-workflows", filename, configToSave);
      setSaveSuccess(`Simple Workflow "${workflowName}" saved successfully as ${filename}.`);
      // Optionally reset form
      // setWorkflowName('');
      // setDescription('');
      // setSteps([]);
    } catch (err) {
      const apiError = err as any;
      console.error("Failed to save simple workflow config:", err);
      setSaveError(apiError.message || `Failed to save workflow ${filename}.`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-4 space-y-6 max-w-3xl mx-auto">
      <h2 className="text-2xl font-semibold text-dracula-pink">Build New Simple Workflow</h2>

      <div className="p-6 bg-dracula-current-line rounded-lg shadow-md space-y-4">
        <div>
          <label htmlFor="workflowName" className="block text-sm font-medium text-dracula-foreground mb-1">Workflow Name</label>
          <input
            type="text"
            id="workflowName"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            placeholder="e.g., Daily Briefing Workflow"
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-dracula-foreground mb-1">Description (Optional)</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="A brief description of what this workflow does."
            className="w-full p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink text-dracula-foreground"
          />
        </div>
      </div>

      <div className="p-6 bg-dracula-current-line rounded-lg shadow-md space-y-4">
        <h3 className="text-lg font-semibold text-dracula-cyan">Workflow Steps (Agent Sequence)</h3>
        {steps.length > 0 ? (
          <ul className="space-y-2">
            {steps.map((step, index) => (
              <li key={`${step}-${index}`} className="flex items-center justify-between p-2 bg-dracula-selection rounded-md">
                <span className="text-dracula-foreground">{index + 1}. {step}</span>
                <button
                  onClick={() => handleRemoveStep(index)}
                  className="text-xs text-dracula-red hover:text-opacity-80"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-dracula-comment text-xs">No steps added yet.</p>
        )}
        <div className="mt-4 flex items-center gap-x-3">
          <select
            value={agentToAdd}
            onChange={(e) => setAgentToAdd(e.target.value)}
            className="flex-grow p-2 rounded-md bg-dracula-background border border-dracula-comment focus:ring-2 focus:ring-dracula-cyan focus:border-dracula-cyan text-dracula-foreground"
            disabled={isLoadingAgents || availableAgents.length === 0}
          >
            <option value="" disabled>-- Select an Agent --</option>
            {availableAgents.map(agent => (
              <option key={agent.id} value={agent.id}>{agent.displayName}</option>
            ))}
          </select>
          <button
            onClick={handleAddStep}
            className="px-4 py-2 text-sm font-medium text-dracula-background bg-dracula-cyan hover:bg-opacity-80 rounded-md focus:outline-none focus:ring-2 focus:ring-dracula-pink"
            disabled={!agentToAdd}
          >
            Add Step
          </button>
        </div>
      </div>

      <div className="flex justify-end items-center space-x-3 mt-6">
        {saveError && <p className="text-sm text-dracula-red">{saveError}</p>}
        {saveSuccess && <p className="text-sm text-dracula-green">{saveSuccess}</p>}
        <button
          onClick={handleSaveWorkflow}
          disabled={isSaving || !workflowName.trim() || steps.length === 0}
          className="px-6 py-2 bg-dracula-green text-dracula-background font-semibold rounded-md hover:bg-opacity-90 focus:outline-none focus:ring-2 focus:ring-dracula-pink disabled:bg-dracula-comment disabled:cursor-not-allowed"
        >
          {isSaving ? 'Saving...' : 'Save Simple Workflow'}
        </button>
      </div>
    </div>
  );
};

export default SimpleWorkflowBuildView;
