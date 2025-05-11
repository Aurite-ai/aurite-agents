import React, { useEffect, useState, useCallback } from 'react';
import useUIStore from '../../../store/uiStore';
import {
  listConfigFiles, // Changed
  getSpecificComponentConfig,
  registerCustomWorkflowAPI,
  registerSimpleWorkflowAPI,
  registerAgentAPI, // Added for agent registration consistency
  registerLlmConfigAPI, // Added for agent LLM config registration
} from '../../../lib/apiClient';
// Corrected import for SelectedSidebarItemType
import type { SelectedSidebarItemType } from '../../../components/layout/ComponentSidebar';
import type { CustomWorkflowConfig, WorkflowConfig, AgentConfig, LLMConfig } from '../../../types/projectManagement'; // Added AgentConfig, LLMConfig
import AgentChatView from './AgentChatView';
import CustomWorkflowExecuteView from './CustomWorkflowExecuteView';
import SimpleWorkflowExecuteView from './SimpleWorkflowExecuteView';

interface ExecutableItem {
  name: string;
  type: SelectedSidebarItemType;
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
    setAgents([]);
    setSimpleWorkflows([]);
    setCustomWorkflows([]);

    const extractName = (filename: string) => filename.replace(/\.json$/, '');

    try {
      const promises = [];
      if (selectedComponent === null || selectedComponent === 'agents') {
        promises.push(
          listConfigFiles("agents").then(filenames =>
            setAgents(filenames.map(fname => ({ name: extractName(fname), type: 'agents' })))
          )
        );
      }
      if (selectedComponent === null || selectedComponent === 'simple_workflows') {
        promises.push(
          listConfigFiles("simple_workflows").then(filenames =>
            setSimpleWorkflows(filenames.map(fname => ({ name: extractName(fname), type: 'simple_workflows' })))
          )
        );
      }
      if (selectedComponent === null || selectedComponent === 'custom_workflows') {
        promises.push(
          listConfigFiles("custom_workflows").then(filenames =>
            setCustomWorkflows(filenames.map(fname => ({ name: extractName(fname), type: 'custom_workflows' })))
          )
        );
      }
      await Promise.all(promises);
    } catch (err) {
      console.error('Error fetching component files for execution:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  }, [selectedComponent]);

  useEffect(() => {
    setSelectedAgentForChat(null);
    setSelectedCustomWorkflowForExecution(null);
    setSelectedSimpleWorkflowForExecution(null); // Reset on component change
    fetchData();
  }, [selectedComponent, fetchData]);

  const performAgentRegistration = async (agentName: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const agentConfig: AgentConfig = await getSpecificComponentConfig("agents", agentName);
      if (agentConfig.llm_config_id) {
        const llmConfig: LLMConfig = await getSpecificComponentConfig("llms", agentConfig.llm_config_id);
        await registerLlmConfigAPI(llmConfig);
      }
      await registerAgentAPI(agentConfig);
      setIsLoading(false);
      return true;
    } catch (err) {
      console.error(`Error registering agent ${agentName}:`, err);
      const apiError = err as any;
      setError(apiError.message || `Failed to register agent ${agentName}.`);
      setIsLoading(false);
      return false;
    }
  };

  const performCustomWorkflowRegistration = async (workflowName: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const config: CustomWorkflowConfig = await getSpecificComponentConfig("custom_workflows", workflowName);
      await registerCustomWorkflowAPI(config);
      setIsLoading(false);
      return true;
    } catch (err) {
      console.error(`Error registering custom workflow ${workflowName}:`, err);
      const apiError = err as any;
      setError(apiError.message || `Failed to register custom workflow ${workflowName}.`);
      setIsLoading(false);
      return false;
    }
  };

  // Removed the first, incomplete handleItemSelect here.
  // The consolidated one is below.

  const performSimpleWorkflowRegistration = async (workflowName: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const config: WorkflowConfig = await getSpecificComponentConfig("simple_workflows", workflowName); // Reverted "workflows" back to "simple_workflows"
      await registerSimpleWorkflowAPI(config);
      setIsLoading(false);
      return true;
    } catch (err) {
      console.error(`Error registering simple workflow ${workflowName}:`, err);
      const apiError = err as any;
      setError(apiError.message || `Failed to register simple workflow ${workflowName}.`);
      setIsLoading(false);
      return false;
    }
  };

  const handleItemSelect = async (item: ExecutableItem) => {
    if (item.type === 'agents') {
      const registrationSuccess = await performAgentRegistration(item.name);
      if (registrationSuccess) {
        setSelectedAgentForChat(item.name);
        setSelectedCustomWorkflowForExecution(null);
        setSelectedSimpleWorkflowForExecution(null);
      }
    } else if (item.type === 'custom_workflows') {
      const registrationSuccess = await performCustomWorkflowRegistration(item.name);
      if (registrationSuccess) {
        setSelectedCustomWorkflowForExecution(item.name);
        setSelectedAgentForChat(null);
        setSelectedSimpleWorkflowForExecution(null);
      }
    } else if (item.type === 'simple_workflows') {
      const registrationSuccess = await performSimpleWorkflowRegistration(item.name);
      if (registrationSuccess) {
        setSelectedSimpleWorkflowForExecution(item.name);
        setSelectedAgentForChat(null);
        setSelectedCustomWorkflowForExecution(null);
      }
    } else {
      console.log(`Selected ${item.type}: ${item.name} - Execution UI TBD`);
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
            <li key={`${item.type}-${item.name}`}>
              <button
                onClick={() => handleItemSelect(item)}
                className={`w-full text-left p-3 rounded-md text-sm transition-colors duration-150 ease-in-out
                  focus:outline-none focus:ring-2 focus:ring-dracula-cyan
                  bg-dracula-current-line hover:bg-opacity-80 text-dracula-foreground focus:bg-dracula-comment focus:bg-opacity-50
                `}
              >
                {item.name}
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
