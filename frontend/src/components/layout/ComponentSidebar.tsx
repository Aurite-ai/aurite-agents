import React from 'react';

export type ComponentType = 'clients' | 'agents' | 'simple_workflows' | 'custom_workflows';

interface ComponentSidebarProps {
  selectedComponent: ComponentType;
  onSelectComponent: (component: ComponentType) => void;
}

const components: { id: ComponentType; label: string }[] = [
  { id: 'clients', label: 'Clients' },
  { id: 'agents', label: 'Agents' },
  { id: 'simple_workflows', label: 'Simple Workflows' },
  { id: 'custom_workflows', label: 'Custom Workflows' },
];

const ComponentSidebar: React.FC<ComponentSidebarProps> = ({
  selectedComponent,
  onSelectComponent,
}) => {
  return (
    <aside className="w-64 bg-dracula-background p-4 space-y-2 shadow-lg border-r border-dracula-current-line">
      <h3 className="px-2 py-1 text-xs font-semibold text-dracula-comment uppercase tracking-wider">
        Component Types
      </h3>
      {components.map((component) => (
        <button
          key={component.id}
          onClick={() => onSelectComponent(component.id)}
          className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-dracula-pink
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
    </aside>
  );
};

export default ComponentSidebar;
