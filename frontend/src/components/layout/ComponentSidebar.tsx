import React from 'react';

// Added 'projects' and 'llms' to ComponentType
export type ComponentType = 'clients' | 'agents' | 'llms' | 'simple_workflows' | 'custom_workflows' | 'projects';

interface ComponentSidebarProps {
  selectedComponent: ComponentType | null; // Allow null if nothing is selected initially or for project section
  onSelectComponent: (component: ComponentType) => void;
}

const componentTypes: { id: ComponentType; label: string }[] = [
  { id: 'clients', label: 'Clients' },
  { id: 'agents', label: 'Agents' },
  { id: 'llms', label: 'LLMs' }, // Added LLMs
  { id: 'simple_workflows', label: 'Simple Workflows' },
  { id: 'custom_workflows', label: 'Custom Workflows' },
];

// Define a new type for the "Projects" section item
const projectComponentItem: { id: ComponentType; label: string } = {
  id: 'projects',
  label: 'Active Project Files',
};

const ComponentSidebar: React.FC<ComponentSidebarProps> = ({
  selectedComponent,
  onSelectComponent,
}) => {
  return (
    <aside className="w-64 bg-dracula-background p-4 space-y-4 shadow-lg border-r border-dracula-current-line">
      <div>
        <h3 className="px-2 py-1 text-xs font-semibold text-dracula-comment uppercase tracking-wider mb-1">
          Component Types
        </h3>
        {componentTypes.map((component) => (
          <button
            key={component.id}
            onClick={() => onSelectComponent(component.id)}
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

      {/* Divider */}
      <hr className="border-dracula-current-line my-3" />

      <div>
        <h3 className="px-2 py-1 text-xs font-semibold text-dracula-comment uppercase tracking-wider mb-1">
          Project Management
        </h3>
        <button
          key={projectComponentItem.id}
          onClick={() => onSelectComponent(projectComponentItem.id)}
          className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-dracula-pink bg-transparent
            ${
              selectedComponent === projectComponentItem.id
                ? 'bg-dracula-green text-dracula-background font-semibold' // Distinct selection style for project
                : 'text-dracula-foreground hover:bg-dracula-current-line hover:text-dracula-foreground'
            }
          `}
        >
          {projectComponentItem.label}
        </button>
      </div>
    </aside>
  );
};

export default ComponentSidebar;
