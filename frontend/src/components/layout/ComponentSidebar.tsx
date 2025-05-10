import React from 'react';
import useUIStore from '../../store/uiStore'; // Import useUIStore to access selectedAction

// Combined type for all selectable items in the sidebar, used by Config and Execute views
export type ConfigurableComponentType = 'clients' | 'agents' | 'llms' | 'simple_workflows' | 'custom_workflows' | 'projects';
export type ExecutableComponentType = 'agents' | 'simple_workflows' | 'custom_workflows'; // LLMs are not directly "executed" in the same way via UI for now

// Union type for what `selectedComponent` in uiStore can hold
export type SelectedSidebarItemType = ConfigurableComponentType | ExecutableComponentType;


interface ComponentSidebarProps {
  // selectedComponent is now derived from useUIStore, so not needed as prop if sidebar directly uses the store
  // onSelectComponent is also from useUIStore
}

const configurableComponentTypes: { id: ConfigurableComponentType; label: string }[] = [
  { id: 'clients', label: 'Clients' },
  { id: 'agents', label: 'Agents' },
  { id: 'llms', label: 'LLMs' },
  { id: 'simple_workflows', label: 'Simple Workflows' },
  { id: 'custom_workflows', label: 'Custom Workflows' },
];

const projectManagementItem: { id: ConfigurableComponentType; label: string } = {
  id: 'projects',
  label: 'Active Project Files',
};

const executableComponentTypes: { id: ExecutableComponentType; label: string }[] = [
  { id: 'agents', label: 'Agents' },
  { id: 'simple_workflows', label: 'Simple Workflows' },
  { id: 'custom_workflows', label: 'Custom Workflows' },
];


const ComponentSidebar: React.FC<ComponentSidebarProps> = () => {
  const { selectedAction, selectedComponent, setSelectedComponent } = useUIStore();

  const renderConfigureModeItems = () => (
    <>
      <div>
        <h3 className="px-2 py-1 text-xs font-semibold text-dracula-comment uppercase tracking-wider mb-1">
          Component Types
        </h3>
        {configurableComponentTypes.map((component) => (
          <button
            key={`config-${component.id}`}
            onClick={() => setSelectedComponent(component.id as SelectedSidebarItemType)}
            className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-dracula-pink bg-transparent
              ${
                selectedComponent === component.id
                  ? 'bg-dracula-purple text-dracula-foreground'
                  : 'text-dracula-foreground hover:bg-dracula-current-line hover:text-dracula-foreground'
              }
            `}
          >
            {component.label}
          </button>
        ))}
      </div>
      <hr className="border-dracula-current-line my-3" />
      <div>
        <h3 className="px-2 py-1 text-xs font-semibold text-dracula-comment uppercase tracking-wider mb-1">
          Project Management
        </h3>
        <button
          key={`config-${projectManagementItem.id}`}
          onClick={() => setSelectedComponent(projectManagementItem.id as SelectedSidebarItemType)}
          className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-dracula-pink bg-transparent
            ${
              selectedComponent === projectManagementItem.id
                ? 'bg-dracula-green text-dracula-background font-semibold'
                : 'text-dracula-foreground hover:bg-dracula-current-line hover:text-dracula-foreground'
            }
          `}
        >
          {projectManagementItem.label}
        </button>
      </div>
    </>
  );

  const renderExecuteModeItems = () => (
    <div>
      <h3 className="px-2 py-1 text-xs font-semibold text-dracula-comment uppercase tracking-wider mb-1">
        Executable Types
      </h3>
      {executableComponentTypes.map((component) => (
        <button
          key={`exec-${component.id}`}
          onClick={() => setSelectedComponent(component.id as SelectedSidebarItemType)}
          className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-dracula-pink bg-transparent
            ${
              selectedComponent === component.id // Use selectedComponent for highlighting
                ? 'bg-dracula-cyan text-dracula-background font-semibold' // Different highlight for execute mode
                : 'text-dracula-foreground hover:bg-dracula-current-line hover:text-dracula-foreground'
            }
          `}
        >
          {component.label}
        </button>
      ))}
    </div>
  );

  return (
    <aside className="w-64 bg-dracula-background p-4 space-y-4 shadow-lg border-r border-dracula-current-line">
      {selectedAction === 'configure' && renderConfigureModeItems()}
      {selectedAction === 'execute' && renderExecuteModeItems()}
      {/* Add other modes like 'build', 'evaluate' here if needed */}
    </aside>
  );
};

export default ComponentSidebar;
