import React from 'react';
import TopNavbar from './TopNavbar';
import ActionTabs from './ActionTabs';
import ComponentSidebar from './ComponentSidebar';
import useUIStore from '../../store/uiStore'; // Adjust path as needed
// Import the general ConfigListView instead of the specific ConfigureAgentsView
import ConfigListView from '../../features/configure/views/ConfigListView';
import ExecuteView from '../../features/execute/views/ExecuteView'; // Import ExecuteView

const Layout: React.FC = () => {
  const {
    selectedAction,
    selectedComponent,
    setSelectedAction,
    setSelectedComponent,
  } = useUIStore();

  return (
    <div className="min-h-screen flex flex-col bg-dracula-background text-dracula-foreground">
      <TopNavbar />
      <ActionTabs
        selectedAction={selectedAction}
        onSelectAction={setSelectedAction}
      />
      <div className="flex flex-1 overflow-hidden">
        <ComponentSidebar
          selectedComponent={selectedComponent}
          onSelectComponent={setSelectedComponent}
        />
        <main className="flex-1 p-6 overflow-y-auto bg-dracula-background">
          {renderDynamicContent()}
        </main>
      </div>
    </div>
  );

  function renderDynamicContent() {
    if (selectedAction === 'configure') {
      return <ConfigListView />; // ConfigListView will use selectedComponent from the store
    }
    if (selectedAction === 'execute') {
      return <ExecuteView />;
    }
    // Add more conditions here for other views as they are created

    // Default placeholder content if no specific view matches
    return (
      <div className="bg-dracula-current-line p-4 rounded-lg shadow-lg border border-dracula-comment">
        <h2 className="text-xl font-semibold mb-2 text-dracula-foreground">
          Selected Action: <span className="text-dracula-pink">{selectedAction}</span>
        </h2>
        <h2 className="text-xl font-semibold text-dracula-foreground">
          Selected Component: <span className="text-dracula-green">{selectedComponent}</span>
        </h2>
        <div className="mt-4">
          <p className="text-dracula-comment">
            Content for this selection will be implemented soon.
          </p>
        </div>
      </div>
    );
  }
};

export default Layout;
