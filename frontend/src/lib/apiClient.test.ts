import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import apiClient from './apiClient';
import useAuthStore from '../store/authStore';

// Mock the auth store
const mockClearAuth = vi.fn();
const initialStoreState = useAuthStore.getState();

// Mock fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('apiClient', () => {
  beforeEach(() => {
    useAuthStore.setState({
      ...initialStoreState, // Reset to actual initial state
      apiKey: null, // Ensure apiKey is null initially for tests
      isAuthenticated: false,
      // Overwrite clearAuth with our mock for this test suite
      clearAuth: mockClearAuth,
    });
    mockFetch.mockClear();
    mockClearAuth.mockClear();
    sessionStorage.clear(); // Ensure sessionStorage is clean for apiKey checks
  });

  afterEach(() => {
    vi.restoreAllMocks(); // Restore fetch and any other global mocks
  });

  it('should add X-API-Key header if apiKey exists in store', async () => {
    const testKey = 'test-api-key-123';
    act(() => {
      useAuthStore.setState({ apiKey: testKey, isAuthenticated: true });
    });
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) } as Response);

    await apiClient('/test-endpoint');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const fetchOptions = mockFetch.mock.calls[0][1] as RequestInit;
    expect(fetchOptions.headers).toBeDefined();
    const headers = new Headers(fetchOptions.headers);
    expect(headers.get('X-API-Key')).toBe(testKey);
  });

  it('should not add X-API-Key header if apiKey does not exist in store', async () => {
    act(() => {
      useAuthStore.setState({ apiKey: null, isAuthenticated: false });
    });
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) } as Response);

    await apiClient('/test-endpoint');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const fetchOptions = mockFetch.mock.calls[0][1] as RequestInit;
    const headers = new Headers(fetchOptions.headers);
    expect(headers.has('X-API-Key')).toBe(false);
  });

  it('should call clearAuth and throw an error on 401 response', async () => {
    mockFetch.mockResolvedValueOnce({ status: 401, ok: false, json: async () => ({ detail: 'Unauthorized' }) } as Response);
    act(() => {
        useAuthStore.setState({ apiKey: 'some-key', isAuthenticated: true });
    });

    await expect(apiClient('/test-401')).rejects.toThrow('Unauthorized - API Key rejected or missing.');
    expect(mockClearAuth).toHaveBeenCalledTimes(1);
  });

  it('should stringify body and set Content-Type for object bodies', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) } as Response);
    const body = { data: 'test' };
    await apiClient('/test-post', { method: 'POST', body });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const fetchOptions = mockFetch.mock.calls[0][1] as RequestInit;
    expect(fetchOptions.body).toBe(JSON.stringify(body));
    const headers = new Headers(fetchOptions.headers);
    expect(headers.get('Content-Type')).toBe('application/json');
  });

  it('should not override existing Content-Type if provided', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) } as Response);
    const body = { data: 'test' };
    await apiClient('/test-post', {
      method: 'POST',
      body,
      headers: { 'Content-Type': 'application/xml' }
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const fetchOptions = mockFetch.mock.calls[0][1] as RequestInit;
     // Body should still be stringified if it's an object, even with custom Content-Type,
     // unless the logic is changed to only stringify for application/json.
     // Current logic stringifies any object body if Content-Type wasn't initially set to application/json.
     // This might need refinement based on desired behavior for other content types.
     // For now, testing current implementation:
    expect(fetchOptions.body).toBe(body); // Body should remain an object if Content-Type is not application/json
    const headers = new Headers(fetchOptions.headers);
    expect(headers.get('Content-Type')).toBe('application/xml');
  });


  it('should rethrow network errors', async () => {
    const networkError = new Error('Network failed');
    mockFetch.mockRejectedValueOnce(networkError);

    await expect(apiClient('/test-network-error')).rejects.toThrow(networkError);
    expect(mockClearAuth).not.toHaveBeenCalled(); // clearAuth should only be called on 401
  });

  it('should correctly construct request URL with /api prefix for relative paths', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({}) } as Response); // Mock for all calls in this test

    await apiClient('/status');
    expect(mockFetch).toHaveBeenCalledWith('/api/status', expect.anything());

    await apiClient('users/list');
    expect(mockFetch).toHaveBeenCalledWith('/api/users/list', expect.anything());

    mockFetch.mockClear(); // Clear mocks before next test or use mockResolvedValueOnce if specific responses are needed per call
  });

  it('should use absolute URL if provided', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) } as Response);
    const absoluteUrl = 'https://example.com/api/data';
    await apiClient(absoluteUrl);
    expect(mockFetch).toHaveBeenCalledWith(absoluteUrl, expect.anything());
  });

  // Helper for act, as it's not directly available in Vitest globals like in Jest/RTL
  // but it's good practice for state updates.
  // For Zustand, direct setState calls in `beforeEach` are often sufficient for setup.
  // For component tests, RTL's `act` is used.
  const act = async (callback: () => void) => {
    callback();
  };
});
