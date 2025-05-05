import { useState } from 'react';
import StatusTab from './components/StatusTab'; // Import the real component
import RegisterTab from './components/RegisterTab'; // Import the real component
import ExecuteTab from './components/ExecuteTab'; // Import the real component

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
import ConfigTab from './components/ConfigTab'; // Import the new component

type TabId = 'register' | 'execute' | 'status' | 'config'; // Add 'config'

function App() {
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
    <div className="min-h-screen bg-gray-100 text-gray-900">
      <div className="max-w-4xl mx-auto bg-white shadow-md rounded-b-lg overflow-hidden">
        <Header />

        {/* Tab Navigation */}
        <nav className="flex bg-gray-700">
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
          {/* Add buttons for future tabs here */}
          {/* <TabButton
            label="Config"
            isActive={activeTab === 'config'}
            onClick={() => setActiveTab('config')}
          /> */}
        </nav>

        {/* Tab Content Area */}
        <main>
          {renderTabContent()}
        </main>

        {/* Result Area (Placeholder - might move into specific tabs later) */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <h3 className="text-lg font-semibold mb-2">Result</h3>
          <pre id="result-display" className="bg-gray-200 p-3 rounded text-sm overflow-x-auto">
            No result yet.
          </pre>
        </div>
      </div>
    </div>
  );
}

export default App;
