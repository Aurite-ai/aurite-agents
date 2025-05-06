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
    <div className="bg-neutral-750 shadow-sm"> {/* Slightly different shade for tab bar */}
      <div className="container mx-auto flex px-4">
        {actions.map((action) => (
          <button
            key={action.id}
            onClick={() => onSelectAction(action.id)}
            className={`py-3 px-6 font-medium text-sm border-b-2 transition-colors duration-150 ease-in-out focus:outline-none
              ${
                selectedAction === action.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-neutral-400 hover:text-neutral-200 hover:border-neutral-500'
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
