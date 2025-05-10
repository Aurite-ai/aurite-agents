import React, { useEffect, useState, useCallback } from 'react';
import useUIStore from '../../../store/uiStore';
import {
  listRegisteredAgents,
  listRegisteredSimpleWorkflows,
  listRegisteredCustomWorkflows
} from '../../../lib/apiClient';
// Corrected import for SelectedSidebarItemType
import type { SelectedSidebarItemType } from '../../../components/layout/ComponentSidebar';
import AgentChatView from './AgentChatView'; // Assuming AgentChatView.tsx is in the same directory

interface ExecutableItem {
  name: string;
  type: SelectedSidebarItemType; // Changed from ExecutableComponentType
}

const ExecuteView: React.FC = () => {
  const { selectedComponent } = useUIStore() as { selectedComponent: SelectedSidebarItemType | null };

  const [agents, setAgents] = useState<ExecutableItem[]>([]);
  const [simpleWorkflows, setSimpleWorkflows] = useState<ExecutableItem[]>([]);
  const [customWorkflows, setCustomWorkflows] = useState<ExecutableItem[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedAgentForChat, setSelectedAgentForChat] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setAgents([]);
    setSimpleWorkflows([]);
    setCustomWorkflows([]);

    try {
      const promises = [];
      if (selectedComponent === null || selectedComponent === 'agents') {
        promises.push(listRegisteredAgents().then(data => setAgents(data.map(name => ({ name, type: 'agents' })))));
      }
      if (selectedComponent === null || selectedComponent === 'simple_workflows') {
        promises.push(listRegisteredSimpleWorkflows().then(data => setSimpleWorkflows(data.map(name => ({ name, type: 'simple_workflows' })))));
      }
      if (selectedComponent === null || selectedComponent === 'custom_workflows') {
        promises.push(listRegisteredCustomWorkflows().then(data => setCustomWorkflows(data.map(name => ({ name, type: 'custom_workflows' })))));
      }
      await Promise.all(promises);
    } catch (err) {
      console.error('Error fetching executable components:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  }, [selectedComponent]);

  useEffect(() => {
    setSelectedAgentForChat(null);
    fetchData();
  }, [selectedComponent, fetchData]);

  const handleItemSelect = (item: ExecutableItem) => {
    if (item.type === 'agents') {
      setSelectedAgentForChat(item.name);
    } else {
      console.log(`Selected ${item.type}: ${item.name} - Execution UI TBD`);
    }
  };

  const handleCloseChat = () => {
    setSelectedAgentForChat(null);
  };

  if (selectedAgentForChat) {
    return <AgentChatView agentName={selectedAgentForChat} onClose={handleCloseChat} />;
  }

  const renderListSection = (
    title: string,
    items: ExecutableItem[],
    itemTypeFilter: SelectedSidebarItemType // Changed from ExecutableComponentType
  ) => {
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
      {!selectedAgentForChat && (
        <h3 className="text-lg font-semibold text-dracula-purple mb-4">
          {selectedComponent ? `Execute ${selectedComponent.charAt(0).toUpperCase() + selectedComponent.slice(1)}` : "Select Component to Execute"}
        </h3>
      )}

      {renderListSection('Agents', agents, 'agents')}
      {renderListSection('Simple Workflows', simpleWorkflows, 'simple_workflows')}
      {renderListSection('Custom Workflows', customWorkflows, 'custom_workflows')}

      {noComponentsAvailable && !isLoading && (
        <p className="text-dracula-comment">
          {selectedComponent ? `No ${selectedComponent} available for execution.` : "No executable components found."}
        </p>
      )}
    </div>
  );
};

export default ExecuteView; // Exporting as ExecuteView
