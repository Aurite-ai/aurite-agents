import React from 'react';

export type ActionType = 'build' | 'configure' | 'execute' | 'evaluate';

interface ActionTabsProps {
  selectedAction: ActionType;
  onSelectAction: (action: ActionType) => void;
}

const actions: { id: ActionType; label: string }[] = [
  { id: 'build', label: 'Build' },
  { id: 'configure', label: 'Configure' },
  { id: 'execute', label: 'Execute' },
  { id: 'evaluate', label: 'Evaluate' },
];

const ActionTabs: React.FC<ActionTabsProps> = ({ selectedAction, onSelectAction }) => {
  return (
    <div className="bg-dracula-background shadow-sm border-b border-dracula-current-line">
      <div className="container mx-auto flex px-4">
        {actions.map((action) => (
          <button
            key={action.id}
            onClick={() => onSelectAction(action.id)}
            // Added bg-transparent to ensure no default button background interferes
            // Added a subtle background for the selected tab for better visual distinction
            className={`py-3 px-6 font-medium text-sm border-b-2 transition-colors duration-150 ease-in-out focus:outline-none focus:border-dracula-pink bg-transparent
              ${
                selectedAction === action.id
                  ? 'border-dracula-pink text-dracula-pink bg-dracula-current-line bg-opacity-50' // Selected: pink border, pink text, subtle bg
                  : 'border-transparent text-dracula-comment hover:text-dracula-foreground hover:border-dracula-comment' // Not selected: transparent border, comment text
              }
            `}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default ActionTabs;
