import React, { useEffect, useState, useCallback } from 'react';
import useUIStore from '../../../store/uiStore';
import {
  listConfigFiles, // Changed
  getSpecificComponentConfig,
  registerCustomWorkflowAPI,
  registerSimpleWorkflowAPI,
  registerAgentAPI,
  registerLlmConfigAPI,
  getActiveProjectComponentConfig,
  getConfigFileContent, // Added
  listActiveHostClients, // Added for new logic
  // Assuming registerClientAPI will be added or is available in apiClient
  registerClientAPI, // Added import
} from '../../../lib/apiClient';
// Corrected import for SelectedSidebarItemType
import type { SelectedSidebarItemType } from '../../../components/layout/ComponentSidebar';
import type { CustomWorkflowConfig, WorkflowConfig, AgentConfig, LLMConfig, ClientConfig } from '../../../types/projectManagement'; // Added ClientConfig
import AgentChatView from './AgentChatView';
import CustomWorkflowExecuteView from './CustomWorkflowExecuteView';
import SimpleWorkflowExecuteView from './SimpleWorkflowExecuteView';
import {
    listRegisteredAgents, // Keep for project-defined components
    listRegisteredSimpleWorkflows, // Keep for project-defined components
    listRegisteredCustomWorkflows // Keep for project-defined components
} from '../../../lib/apiClient'; // Ensure these are still imported if used below

interface ExecutableItem {
  id: string; // Unique ID (filename without .json or registered name)
  displayName: string; // Name to show in UI
  type: SelectedSidebarItemType;
  source: 'file' | 'project'; // To distinguish origin
}

const ExecuteView: React.FC = () => {
  const { selectedComponent } = useUIStore() as { selectedComponent: SelectedSidebarItemType | null };

  const [agents, setAgents] = useState<ExecutableItem[]>([]);
  const [simpleWorkflows, setSimpleWorkflows] = useState<ExecutableItem[]>([]);
  const [customWorkflows, setCustomWorkflows] = useState<ExecutableItem[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedAgentForChat, setSelectedAgentForChat] = useState<string | null>(null);
  const [selectedCustomWorkflowForExecution, setSelectedCustomWorkflowForExecution] = useState<string | null>(null);
  const [selectedSimpleWorkflowForExecution, setSelectedSimpleWorkflowForExecution] = useState<string | null>(null); // Added

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setAgents([]); // Clear previous lists
    setSimpleWorkflows([]);
    setCustomWorkflows([]);

    const extractNameFromFilename = (filename: string) => filename.replace(/\.json$/, '');

    const fetchAndMergeItems = async (
      uiComponentType: SelectedSidebarItemType, // e.g., 'agents', 'simple_workflows'
      listRegisteredFn: () => Promise<string[]>, // Function to get names from active project
      // API key for listConfigFiles & getConfigFileContent (e.g., "agents", "simple_workflows")
      configFileApiType: "agents" | "simple_workflows" | "custom_workflows" | "llms"
    ): Promise<ExecutableItem[]> => {
      const itemMap = new Map<string, ExecutableItem>();

      // 1. Fetch components from individual config files
      try {
        const filenames = await listConfigFiles(configFileApiType);
        for (const fname of filenames) {
          try {
            const fileContent = await getConfigFileContent(configFileApiType, fname);

            if (Array.isArray(fileContent)) { // File contains a list of components
              fileContent.forEach((componentConfig: any) => {
                const id = componentConfig.name; // Assuming 'name' is the ID field
                if (id && typeof id === 'string') {
                  itemMap.set(id, { id, displayName: id, type: uiComponentType, source: 'file' });
                } else {
                  console.warn(`Component in file ${fname} (type ${configFileApiType}) is missing a 'name' or has invalid name.`);
                }
              });
            } else if (typeof fileContent === 'object' && fileContent !== null) { // File contains a single component object
              const id = fileContent.name || extractNameFromFilename(fname); // Use 'name' field or fallback to filename
              if (id && typeof id === 'string') {
                 itemMap.set(id, { id, displayName: id, type: uiComponentType, source: 'file' });
              } else {
                 console.warn(`Could not determine ID for single component in ${fname} (type ${configFileApiType}).`);
              }
            } else {
              console.warn(`Content of file ${fname} (type ${configFileApiType}) is not an array or a valid object. Skipping.`);
            }
          } catch (fileContentError) {
            console.error(`Error fetching or parsing content of ${fname} for ${configFileApiType}:`, fileContentError);
          }
        }
      } catch (e) {
        console.error(`Error listing config files for ${configFileApiType}:`, e);
      }

      // 2. Fetch project-registered components
      try {
        const registeredNames = await listRegisteredFn();
        registeredNames.forEach(name => {
          if (!itemMap.has(name)) { // Add only if not already present from file-based (file takes precedence)
            itemMap.set(name, { id: name, displayName: name, type: uiComponentType, source: 'project' });
          }
        });
      } catch (e) {
        console.error(`Error listing registered ${uiComponentType}:`, e);
      }
      return Array.from(itemMap.values()).sort((a, b) => a.displayName.localeCompare(b.displayName));
    };

    try {
      const promises = [];
      if (selectedComponent === null || selectedComponent === 'agents') {
        promises.push(fetchAndMergeItems('agents', listRegisteredAgents, 'agents').then(setAgents));
      }
      if (selectedComponent === null || selectedComponent === 'simple_workflows') {
        promises.push(fetchAndMergeItems('simple_workflows', listRegisteredSimpleWorkflows, 'simple_workflows').then(setSimpleWorkflows));
      }
      if (selectedComponent === null || selectedComponent === 'custom_workflows') {
        promises.push(fetchAndMergeItems('custom_workflows', listRegisteredCustomWorkflows, 'custom_workflows').then(setCustomWorkflows));
      }
      await Promise.all(promises);
    } catch (err) {
      console.error('Error fetching and merging executable components:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred while fetching components.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedComponent]); // Removed getConfigFileContent from deps as it's stable from import

  useEffect(() => {
    setSelectedAgentForChat(null);
    setSelectedCustomWorkflowForExecution(null);
    setSelectedSimpleWorkflowForExecution(null); // Reset on component change
    fetchData();
  }, [selectedComponent, fetchData]);

  // getActiveProjectComponentConfig is now directly imported

  const performAgentRegistration = async (item: ExecutableItem): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      let agentConfig: AgentConfig;
      if (item.source === 'project') {
        agentConfig = await getActiveProjectComponentConfig("agents", item.id);
      } else { // source === 'file'
        agentConfig = await getSpecificComponentConfig("agents", item.id);
      }

      if (!agentConfig) throw new Error(`Agent config for ${item.displayName} not found.`);

      // 1. Register dependent clients if not already active
      if (agentConfig.client_ids && agentConfig.client_ids.length > 0) {
        const activeClientIds = await listActiveHostClients();
        const activeClientIdsSet = new Set(activeClientIds);

        for (const clientId of agentConfig.client_ids) {
          if (!activeClientIdsSet.has(clientId)) {
            console.log(`Client ${clientId} for agent ${agentConfig.name} is not active. Attempting to register...`);
            try {
              let clientConfigToRegister: ClientConfig | null = null;
              // Try to get client config from active project first
              try {
                clientConfigToRegister = await getActiveProjectComponentConfig("clients", clientId) as ClientConfig;
              } catch (projectClientError) {
                console.warn(`Client config ${clientId} not found in active project. Trying file-based config.`);
                try {
                  // Ensure getSpecificComponentConfig for "clients" returns ClientConfig
                  clientConfigToRegister = await getSpecificComponentConfig("clients", clientId) as ClientConfig;
                } catch (fileClientError) {
                  console.error(`Client config ${clientId} not found in project or as a file. Cannot register.`);
                  throw new Error(`Required client config ${clientId} for agent ${agentConfig.name} not found.`);
                }
              }

              if (clientConfigToRegister) {
                await registerClientAPI(clientConfigToRegister);
                console.log(`Client ${clientId} registered successfully.`);
              } else {
                // This case should ideally be caught by the errors above if config is truly missing
                throw new Error(`Client config for ${clientId} could not be loaded for agent ${agentConfig.name}.`);
              }
            } catch (clientRegError) {
              console.error(`Error registering client ${clientId} for agent ${agentConfig.name}:`, clientRegError);
              throw clientRegError; // Propagate error to stop agent registration
            }
          } else {
            console.log(`Client ${clientId} for agent ${agentConfig.name} is already active.`);
          }
        }
      }

      // 2. Register LLM Config if specified
      if (agentConfig.llm_config_id) {
        let llmConfig: LLMConfig | null = null;
        try {
          // Ensure "llms" is used, not "llm_configs"
          llmConfig = await getActiveProjectComponentConfig("llms", agentConfig.llm_config_id);
        } catch (projectLlmError) {
          console.warn(`LLM config ${agentConfig.llm_config_id} not found in project, trying file-based.`);
          try {
            llmConfig = await getSpecificComponentConfig("llms", agentConfig.llm_config_id);
          } catch (fileLlmError) {
            console.error(`LLM config ${agentConfig.llm_config_id} not found in project or as file.`);
            throw new Error(`Required LLM config ${agentConfig.llm_config_id} not found for agent ${agentConfig.name}.`);
          }
        }
        if (llmConfig) {
          await registerLlmConfigAPI(llmConfig);
          console.log(`LLM Config ${agentConfig.llm_config_id} registered successfully for agent ${agentConfig.name}.`);
        } else {
           throw new Error(`LLM config ${agentConfig.llm_config_id} could not be loaded for agent ${agentConfig.name}.`);
        }
      }

      // 3. Register the Agent itself
      await registerAgentAPI(agentConfig);
      console.log(`Agent ${agentConfig.name} registered successfully.`);
      setIsLoading(false);
      return true;
    } catch (err) {
      console.error(`Error registering agent ${item.displayName}:`, err);
      const apiError = err as any;
      setError(apiError.message || `Failed to register agent ${item.displayName}.`);
      setIsLoading(false);
      return false;
    }
  };

  const performCustomWorkflowRegistration = async (item: ExecutableItem): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      let config: CustomWorkflowConfig;
      if (item.source === 'project') {
        config = await getActiveProjectComponentConfig("custom_workflows", item.id);
      } else { // source === 'file'
        config = await getSpecificComponentConfig("custom_workflows", item.id);
      }
      if (!config) throw new Error(`Custom workflow config for ${item.displayName} not found.`);
      await registerCustomWorkflowAPI(config);
      setIsLoading(false);
      return true;
    } catch (err) {
      console.error(`Error registering custom workflow ${item.displayName}:`, err);
      const apiError = err as any;
      setError(apiError.message || `Failed to register custom workflow ${item.displayName}.`);
      setIsLoading(false);
      return false;
    }
  };

  const performSimpleWorkflowRegistration = async (item: ExecutableItem): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      let config: WorkflowConfig;
      if (item.source === 'project') {
        config = await getActiveProjectComponentConfig("simple_workflows", item.id);
      } else { // source === 'file'
        config = await getSpecificComponentConfig("simple_workflows", item.id);
      }
      if (!config) throw new Error(`Simple workflow config for ${item.displayName} not found.`);
      await registerSimpleWorkflowAPI(config);
      setIsLoading(false);
      return true;
    } catch (err) {
      console.error(`Error registering simple workflow ${item.displayName}:`, err);
      const apiError = err as any;
      setError(apiError.message || `Failed to register simple workflow ${item.displayName}.`);
      setIsLoading(false);
      return false;
    }
  };

  const handleItemSelect = async (item: ExecutableItem) => {
    if (item.type === 'agents') {
      const registrationSuccess = await performAgentRegistration(item);
      if (registrationSuccess) {
        setSelectedAgentForChat(item.id); // Use item.id
        setSelectedCustomWorkflowForExecution(null);
        setSelectedSimpleWorkflowForExecution(null);
      }
    } else if (item.type === 'custom_workflows') {
      const registrationSuccess = await performCustomWorkflowRegistration(item);
      if (registrationSuccess) {
        setSelectedCustomWorkflowForExecution(item.id); // Use item.id
        setSelectedAgentForChat(null);
        setSelectedSimpleWorkflowForExecution(null);
      }
    } else if (item.type === 'simple_workflows') {
      const registrationSuccess = await performSimpleWorkflowRegistration(item);
      if (registrationSuccess) {
        setSelectedSimpleWorkflowForExecution(item.id); // Use item.id
        setSelectedAgentForChat(null);
        setSelectedCustomWorkflowForExecution(null);
      }
    } else {
      console.log(`Selected ${item.type}: ${item.displayName} - Execution UI TBD`);
      setSelectedAgentForChat(null);
      setSelectedCustomWorkflowForExecution(null);
      setSelectedSimpleWorkflowForExecution(null);
    }
  };

  const handleCloseChat = () => {
    setSelectedAgentForChat(null);
  };

  const handleCloseCustomWorkflowView = () => {
    setSelectedCustomWorkflowForExecution(null);
  };

  const handleCloseSimpleWorkflowView = () => {
    setSelectedSimpleWorkflowForExecution(null);
  };

  if (selectedAgentForChat) {
    return <AgentChatView agentName={selectedAgentForChat} onClose={handleCloseChat} />;
  }

  if (selectedCustomWorkflowForExecution) {
    return <CustomWorkflowExecuteView workflowName={selectedCustomWorkflowForExecution} onClose={handleCloseCustomWorkflowView} />;
  }

  if (selectedSimpleWorkflowForExecution) {
    return <SimpleWorkflowExecuteView workflowName={selectedSimpleWorkflowForExecution} onClose={handleCloseSimpleWorkflowView} />;
  }

  const renderListSection = (
    title: string,
    items: ExecutableItem[],
    itemTypeFilter: SelectedSidebarItemType
  ) => {
    // If a specific view (chat, custom workflow, or simple workflow) is active, don't render lists.
    if (selectedAgentForChat || selectedCustomWorkflowForExecution || selectedSimpleWorkflowForExecution) {
      return null;
    }

    if (selectedComponent !== null && selectedComponent !== itemTypeFilter) {
      return null;
    }
    if (items.length === 0 && selectedComponent === itemTypeFilter) {
        return (
            <div className="mb-6">
                <h4 className="text-xl font-semibold text-dracula-cyan mb-3">{title}</h4>
                <p className="text-dracula-comment">No {title.toLowerCase()} available for execution.</p>
            </div>
        );
    }
    if (items.length === 0) return null;

    return (
      <div className="mb-6">
        <h4 className="text-xl font-semibold text-dracula-cyan mb-3">{title}</h4>
        <ul className="space-y-2">
          {items.map(item => (
            <li key={`${item.type}-${item.id}`}> {/* Changed item.name to item.id */}
              <button
                onClick={() => handleItemSelect(item)}
                className={`w-full text-left p-3 rounded-md text-sm transition-colors duration-150 ease-in-out
                  focus:outline-none focus:ring-2 focus:ring-dracula-cyan
                  bg-dracula-current-line hover:bg-opacity-80 text-dracula-foreground focus:bg-dracula-comment focus:bg-opacity-50
                `}
              >
                {item.displayName} {/* Use item.displayName */}
              </button>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  if (isLoading) {
    return <p className="text-dracula-comment p-1">Loading executable components...</p>;
  }

  if (error) {
    return <p className="text-dracula-red p-1">Error: {error}</p>;
  }

  const noComponentsAvailable = agents.length === 0 && simpleWorkflows.length === 0 && customWorkflows.length === 0;

  return (
    <div className="p-1">
      {/* Conditional Title: Only show if no specific execution view is active */}
      {!selectedAgentForChat && !selectedCustomWorkflowForExecution && !selectedSimpleWorkflowForExecution && (
        <h3 className="text-lg font-semibold text-dracula-purple mb-4">
          {selectedComponent ? `Execute ${selectedComponent.charAt(0).toUpperCase() + selectedComponent.slice(1)}` : "Select Component to Execute"}
        </h3>
      )}

      {renderListSection('Agents', agents, 'agents')}
      {renderListSection('Simple Workflows', simpleWorkflows, 'simple_workflows')}
      {renderListSection('Custom Workflows', customWorkflows, 'custom_workflows')}

      {/* Conditional "No components" message: Only show if no specific execution view is active */}
      {!selectedAgentForChat && !selectedCustomWorkflowForExecution && !selectedSimpleWorkflowForExecution && noComponentsAvailable && !isLoading && (
        <p className="text-dracula-comment">
          {selectedComponent ? `No ${selectedComponent} available for execution.` : "No executable components found."}
        </p>
      )}
    </div>
  );
};

export default ExecuteView;
