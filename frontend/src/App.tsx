import { useEffect } from 'react';
import useAuthStore from './store/authStore';
import ApiKeyModal from './components/auth/ApiKeyModal';
import Layout from './components/layout/Layout'; // Import the new Layout component
// The specific tab components (StatusTab, RegisterTab, etc.) will be rendered by Layout's children logic later.

// Main application content, to be rendered when authenticated
const MainAppContent = () => {
  // The old tab logic (activeTab, renderTabContent, Header, TabButton) is removed.
  // Layout component now handles the main structure.
  // The children of Layout will eventually render dynamic views based on uiStore.
  // Layout now handles its own content rendering based on the uiStore.
  return (
    <Layout />
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
