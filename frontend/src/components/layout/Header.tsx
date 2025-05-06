import React from 'react';
import useUIStore from '../../store/uiStore'; // For selectedAction and onSelectAction

// Copied from ActionTabs.tsx
export type ActionType = 'build' | 'configure' | 'execute' | 'evaluate';
const actions: { id: ActionType; label: string }[] = [
  { id: 'build', label: 'Build' },
  { id: 'configure', label: 'Configure' },
  { id: 'execute', label: 'Execute' },
  { id: 'evaluate', label: 'Evaluate' },
];

const Header: React.FC = () => { // Renamed component to Header
  const { selectedAction, setSelectedAction } = useUIStore();

  return (
    <nav className="w-full bg-dracula-current-line text-dracula-foreground p-4 shadow-lg">
      <div className="w-full flex items-center"> {/* Removed container and mx-auto */}
        {/* Left Group: Logo and Title */}
        <div className="flex items-center space-x-4 mr-6"> {/* Added mr-6 for spacing */}
          <div className="w-8 h-8 bg-dracula-purple rounded-full flex items-center justify-center text-dracula-background font-bold">
            A
          </div>
          <h1 className="text-xl font-semibold text-dracula-foreground">Aurite AI Studio</h1>
        </div>

        {/* Middle Group: Action Tabs */}
        <div className="flex items-center space-x-2">
          {actions.map((action) => (
            <button
              key={action.id}
              onClick={() => setSelectedAction(action.id)}
              className={`py-2 px-4 font-medium text-sm rounded-md transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-dracula-pink focus:ring-opacity-75
                ${
                  selectedAction === action.id
                    ? 'bg-dracula-pink text-dracula-background' // Selected
                    : 'text-dracula-comment hover:text-dracula-foreground hover:bg-dracula-comment hover:bg-opacity-25' // Not selected
                }
              `}
            >
              {action.label}
            </button>
          ))}
        </div>

        {/* Right Group: User Profile Icon - Pushed to the right by ml-auto */}
        <div className="flex items-center space-x-4 ml-auto">
          <div className="w-8 h-8 bg-dracula-comment bg-opacity-50 rounded-full flex items-center justify-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-5 h-5 text-dracula-foreground"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
            </svg>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Header; // Exporting as Header
