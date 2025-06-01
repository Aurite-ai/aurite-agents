import React, { useState } from 'react'; // Removed useEffect
import useAuthStore from '../../store/authStore';

const ApiKeyModal: React.FC = () => {
  const { isAuthenticated, isLoading, error, validateApiKey } = useAuthStore();
  const [localApiKey, setLocalApiKey] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (localApiKey.trim()) {
      await validateApiKey(localApiKey.trim());
      // If validation is successful, the store will set isAuthenticated to true,
      // and the modal will be hidden by the logic in App.tsx (or a layout component).
      // If validation fails, the error will be displayed.
    }
  };

  // If already authenticated, don't render the modal content
  // This check might be redundant if the parent component handles visibility,
  // but it's a good safeguard.
  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-dracula-background bg-opacity-75 backdrop-blur-sm">
      <div className="bg-dracula-current-line p-8 rounded-lg shadow-xl w-full max-w-md border border-dracula-comment">
        <h2 className="text-2xl font-semibold mb-6 text-center text-dracula-foreground">Enter API Key</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="apiKey" className="block text-sm font-medium text-dracula-foreground mb-1">
              API Key
            </label>
            <input
              type="password"
              id="apiKey"
              value={localApiKey}
              onChange={(e) => setLocalApiKey(e.target.value)}
              className="w-full px-4 py-2 border border-dracula-comment rounded-md bg-dracula-background text-dracula-foreground placeholder-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink outline-none"
              placeholder="Enter your API key"
              required
              disabled={isLoading}
            />
          </div>

          {error && (
            <div className="mb-4 p-3 bg-dracula-red bg-opacity-80 text-dracula-foreground border border-dracula-red rounded-md text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="w-full bg-dracula-pink hover:bg-opacity-80 text-dracula-background font-semibold py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-dracula-purple focus:ring-opacity-50 transition duration-150 ease-in-out disabled:opacity-50 disabled:bg-dracula-comment"
            disabled={isLoading}
          >
            {isLoading ? 'Validating...' : 'Submit'}
          </button>
        </form>
        <p className="mt-4 text-xs text-dracula-comment text-center">
          The API key will be stored in session storage.
        </p>
      </div>
    </div>
  );
};

export default ApiKeyModal;
