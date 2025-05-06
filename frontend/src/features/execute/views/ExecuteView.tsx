import React, { useEffect, useState } from 'react';
import apiClient from '../../../lib/apiClient';
import useUIStore from '../../../store/uiStore';
import type { ComponentType } from '../../../components/layout/ComponentSidebar';

interface ExecutableComponent {
  name: string;
  type: 'agent' | 'workflow' | 'custom_workflow'; // To distinguish in a unified list if needed
}

const ExecuteView: React.FC = () => {
  const { selectedComponent, setSelectedComponent } = useUIStore(); // We might use selectedComponent to pre-select or filter

  const [agents, setAgents] = useState<ExecutableComponent[]>([]);
  const [workflows, setWorkflows] = useState<ExecutableComponent[]>([]);
  const [customWorkflows, setCustomWorkflows] = useState<ExecutableComponent[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // State for the selected component to execute
  const [selectedExecutable, setSelectedExecutable] = useState<ExecutableComponent | null>(null);

  useEffect(() => {
    const fetchAllComponents = async () => {
      setIsLoading(true);
      setError(null);
      setAgents([]);
      setWorkflows([]);
      setCustomWorkflows([]);

      try {
        const [agentsRes, workflowsRes, customWorkflowsRes] = await Promise.all([
          apiClient('/components/agents'),
          apiClient('/components/workflows'),
          apiClient('/components/custom_workflows'),
        ]);

        if (!agentsRes.ok) throw new Error(`Failed to fetch agents: ${await agentsRes.text()}`);
        const agentsData: string[] = await agentsRes.json();
        setAgents(agentsData.map(name => ({ name, type: 'agent' })));

        if (!workflowsRes.ok) throw new Error(`Failed to fetch workflows: ${await workflowsRes.text()}`);
        const workflowsData: string[] = await workflowsRes.json();
        setWorkflows(workflowsData.map(name => ({ name, type: 'workflow' })));

        if (!customWorkflowsRes.ok) throw new Error(`Failed to fetch custom workflows: ${await customWorkflowsRes.text()}`);
        const customWorkflowsData: string[] = await customWorkflowsRes.json();
        setCustomWorkflows(customWorkflowsData.map(name => ({ name, type: 'custom_workflow' })));

      } catch (err) {
        console.error('Error fetching executable components:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setIsLoading(false);
      }
    };
    fetchAllComponents();
  }, []); // Fetch once on mount

  const handleSelectExecutable = (component: ExecutableComponent) => {
    setSelectedExecutable(component);
    // Update the global component type in uiStore if it's different,
    // this helps keep the sidebar in sync if we want that behavior.
    // Map our local 'type' to the ComponentType used by the sidebar.
    let newSelectedComponentType: ComponentType | null = null;
    if (component.type === 'agent') newSelectedComponentType = 'agents';
    else if (component.type === 'workflow') newSelectedComponentType = 'simple_workflows';
    else if (component.type === 'custom_workflow') newSelectedComponentType = 'custom_workflows';

    if (newSelectedComponentType && selectedComponent !== newSelectedComponentType) {
      setSelectedComponent(newSelectedComponentType);
    }
    console.log('Selected for execution:', component);
    // Next step will be to show input form based on this selection
  };

  const renderListComponent = (
    title: string,
    items: ExecutableComponent[],
    currentType: 'agent' | 'workflow' | 'custom_workflow'
  ) => {
    if (items.length === 0) return null; // Don't render section if no items
    return (
      <div className="mb-6">
        <h4 className="text-md font-semibold text-dracula-cyan mb-2 border-b border-dracula-comment pb-1">
          {title}
        </h4>
        <ul className="space-y-1 max-h-60 overflow-y-auto pr-2">
          {items.map(item => (
            <li key={`${item.type}-${item.name}`}>
              <button
                onClick={() => handleSelectExecutable(item)}
                className={`w-full text-left p-2 rounded-md text-sm transition-colors duration-150 ease-in-out
                  ${
                    selectedExecutable?.name === item.name && selectedExecutable?.type === item.type
                      ? 'bg-dracula-pink text-dracula-background'
                      : 'bg-dracula-current-line hover:bg-opacity-80 text-dracula-foreground focus:bg-dracula-comment focus:bg-opacity-50'
                  }
                  focus:outline-none focus:ring-1 focus:ring-dracula-pink`}
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
    return <p className="text-dracula-comment">Loading executable components...</p>;
  }

  if (error) {
    return <p className="text-dracula-red">Error: {error}</p>;
  }

  return (
    <div className="p-1">
      <h3 className="text-lg font-semibold text-dracula-purple mb-4">
        Select Component to Execute
      </h3>

      {renderListComponent('Agents', agents, 'agent')}
      {renderListComponent('Simple Workflows', workflows, 'workflow')}
      {renderListComponent('Custom Workflows', customWorkflows, 'custom_workflow')}

      {selectedExecutable && (
        <div className="mt-6 p-4 bg-dracula-current-line rounded-lg border border-dracula-comment">
          <h4 className="text-md font-semibold text-dracula-green mb-2">
            Selected: {selectedExecutable.name} ({selectedExecutable.type})
          </h4>
          <p className="text-dracula-comment text-sm">
            Next: Implement input form and execution button here (Step 4.2).
          </p>
        </div>
      )}

      {(agents.length === 0 && workflows.length === 0 && customWorkflows.length === 0 && !isLoading) && (
        <p className="text-dracula-comment">No executable components found.</p>
      )}
    </div>
  );
};

export default ExecuteView;
