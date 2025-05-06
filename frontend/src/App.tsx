import { useState, useEffect } from 'react';
import useAuthStore from './store/authStore';
import ApiKeyModal from './components/auth/ApiKeyModal';
import StatusTab from './components/StatusTab'; // Import the real component
import RegisterTab from './components/RegisterTab'; // Import the real component
import ExecuteTab from './components/ExecuteTab'; // Import the real component
import ConfigTab from './components/ConfigTab'; // Import the new component

// Placeholder components (we'll create these properly later)
const Header = () => (
  <header className="bg-gray-800 text-white p-4 text-center">
    <h1 className="text-xl font-bold">Aurite MCP - Agent Framework</h1>
    <p>API Management Interface</p>
  </header>
);

const TabButton = ({ label, isActive, onClick }: { label: string; isActive: boolean; onClick: () => void }) => (
  <button
    className={`flex-1 py-3 px-4 text-white text-sm font-medium transition-colors duration-200 ease-in-out ${
      isActive ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
    }`}
    onClick={onClick}
  >
    {label}
  </button>
);

// Placeholder Tab Content Components
// Remove the placeholder RegisterTab function definition
// Remove the placeholder ExecuteTab function definition
// Remove the placeholder StatusTab function definition
// Add placeholders for future tabs if needed

type TabId = 'register' | 'execute' | 'status' | 'config'; // Add 'config'

// Main application content, to be rendered when authenticated
const MainAppContent = () => {
  const [activeTab, setActiveTab] = useState<TabId>('register'); // Default tab

  const renderTabContent = () => {
    switch (activeTab) {
      case 'register':
        return <RegisterTab />;
      case 'execute':
        return <ExecuteTab />;
      case 'status':
        return <StatusTab />;
      case 'config':
        return <ConfigTab />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-neutral-900 text-neutral-100"> {/* Updated background and text for dark theme */}
      <div className="max-w-4xl mx-auto bg-neutral-800 shadow-xl rounded-b-lg overflow-hidden"> {/* Darker theme for main container */}
        <Header />

        {/* Tab Navigation */}
        <nav className="flex bg-neutral-700"> {/* Darker tabs background */}
          <TabButton
            label="Register"
            isActive={activeTab === 'register'}
            onClick={() => setActiveTab('register')}
          />
          <TabButton
            label="Execute"
            isActive={activeTab === 'execute'}
            onClick={() => setActiveTab('execute')}
          />
          <TabButton
            label="Status"
            isActive={activeTab === 'status'}
            onClick={() => setActiveTab('status')}
          />
          <TabButton
            label="Config Files"
            isActive={activeTab === 'config'}
            onClick={() => setActiveTab('config')}
          />
        </nav>

        {/* Tab Content Area */}
        <main className="p-4 bg-neutral-850"> {/* Slightly different shade for content area if needed, or keep same as container */}
          {renderTabContent()}
        </main>

        {/* Result Area (Placeholder - might move into specific tabs later) */}
        <div className="p-4 border-t border-neutral-700 bg-neutral-800"> {/* Dark theme for result area */}
          <h3 className="text-lg font-semibold mb-2 text-neutral-100">Result</h3>
          <pre id="result-display" className="bg-neutral-900 p-3 rounded text-sm overflow-x-auto text-neutral-200">
            No result yet.
          </pre>
        </div>
      </div>
    </div>
  );
};

function App() {
  const { isAuthenticated, apiKey, validateApiKey } = useAuthStore();

  useEffect(() => {
    // Attempt to validate API key from session storage on initial load
    // This handles the case where the user had a valid key, closed the tab, and reopened it.
    // The store already initializes apiKey from sessionStorage.
    if (apiKey && !isAuthenticated) {
      validateApiKey(apiKey);
    }
  }, [apiKey, isAuthenticated, validateApiKey]);

  if (!isAuthenticated) {
    return <ApiKeyModal />;
  }

  return <MainAppContent />;
}

export default App;
