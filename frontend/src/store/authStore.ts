import { create } from 'zustand';

interface AuthState {
  apiKey: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  setApiKey: (key: string | null) => void;
  validateApiKey: (key: string) => Promise<boolean>;
  clearAuth: () => void;
}

const useAuthStore = create<AuthState>((set, get) => ({
  apiKey: sessionStorage.getItem('apiKey'),
  isAuthenticated: !!sessionStorage.getItem('apiKey'), // Initial check
  isLoading: false,
  error: null,
  setApiKey: (key) => {
    if (key) {
      sessionStorage.setItem('apiKey', key);
      set({ apiKey: key, isAuthenticated: true, error: null });
    } else {
      sessionStorage.removeItem('apiKey');
      set({ apiKey: null, isAuthenticated: false });
    }
  },
  validateApiKey: async (key: string): Promise<boolean> => {
    set({ isLoading: true, error: null });
    try {
      // In a real app, the API base URL would come from an env variable
      const response = await fetch('/status', { // Assuming API is on the same origin
        method: 'GET',
        headers: {
          'X-API-Key': key,
        },
      });

      if (response.ok) {
        get().setApiKey(key); // Use get() to access other actions like setApiKey
        set({ isAuthenticated: true, isLoading: false, error: null });
        return true;
      } else {
        const errorData = await response.json();
        set({
          isAuthenticated: false,
          isLoading: false,
          error: errorData.detail || 'Invalid API Key or API error.',
        });
        sessionStorage.removeItem('apiKey'); // Ensure key is removed on validation failure
        return false;
      }
    } catch (err) {
      console.error('API Key validation error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Network error or API is down.';
      set({ isAuthenticated: false, isLoading: false, error: errorMessage });
      sessionStorage.removeItem('apiKey'); // Ensure key is removed on validation failure
      return false;
    }
  },
  clearAuth: () => {
    sessionStorage.removeItem('apiKey');
    set({ apiKey: null, isAuthenticated: false, error: null, isLoading: false });
  },
}));

export default useAuthStore;
