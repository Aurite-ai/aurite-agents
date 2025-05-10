import React from 'react';
import useUIStore from '../../store/uiStore'; // Import useUIStore to access selectedAction

// Combined type for all selectable items in the sidebar
export type ConfigurableComponentType = 'clients' | 'agents' | 'llms' | 'simple_workflows' | 'custom_workflows' | 'projects';

// SelectedSidebarItemType will now just be ConfigurableComponentType
export type SelectedSidebarItemType = ConfigurableComponentType;


interface ComponentSidebarProps {
  // selectedComponent is now derived from useUIStore, so not needed as prop if sidebar directly uses the store
  // onSelectComponent is also from useUIStore
}

const componentTypes: { id: ConfigurableComponentType; label: string }[] = [
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

// executableComponentTypes is no longer needed as we will use componentTypes for all views.


const ComponentSidebar: React.FC<ComponentSidebarProps> = () => {
  const { selectedComponent, setSelectedComponent } = useUIStore(); // selectedAction is no longer needed here to switch rendering logic

  const renderSidebarItems = () => (
    <>
      <div>
        <h3 className="px-2 py-1 text-xs font-semibold text-dracula-comment uppercase tracking-wider mb-1">
          Component Types
        </h3>
        {componentTypes.map((component) => (
          <button
            key={`sidebar-item-${component.id}`} // Generic key
            onClick={() => setSelectedComponent(component.id as SelectedSidebarItemType)}
            className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-dracula-pink bg-transparent
              ${
                selectedComponent === component.id
                  ? 'bg-dracula-purple text-dracula-foreground' // Consistent highlight for components
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
          key={`sidebar-item-${projectManagementItem.id}`} // Generic key
          onClick={() => setSelectedComponent(projectManagementItem.id as SelectedSidebarItemType)}
          className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-dracula-pink bg-transparent
            ${
              selectedComponent === projectManagementItem.id
                ? 'bg-dracula-green text-dracula-background font-semibold' // Consistent highlight for project management
                : 'text-dracula-foreground hover:bg-dracula-current-line hover:text-dracula-foreground'
            }
          `}
        >
          {projectManagementItem.label}
        </button>
      </div>
    </>
  );

  // renderExecuteModeItems is no longer needed.

  return (
    <aside className="w-64 bg-dracula-background p-4 space-y-4 shadow-lg border-r border-dracula-current-line">
      {renderSidebarItems()}
      {/* The sidebar content is now consistent across all action tabs.
          If specific tabs needed *additional* items, that would require further logic,
          but the request was for them all to look like renderConfigureModeItems. */}
    </aside>
  );
};

export default ComponentSidebar;
