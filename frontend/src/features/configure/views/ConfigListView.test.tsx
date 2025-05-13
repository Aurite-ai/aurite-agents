/// <reference types="vitest/globals" />
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConfigListView from './ConfigListView';
import useUIStore from '../../../store/uiStore';
import apiClient from '../../../lib/apiClient'; // Actual apiClient for mocking its usage
import ConfigEditorView from './ConfigEditorView'; // Import ConfigEditorView

// Mock apiClient and ConfigEditorView
vi.mock('../../../lib/apiClient');
vi.mock('./ConfigEditorView', () => ({
  default: vi.fn(({ componentType, filename, onClose }) => (
    <div data-testid="config-editor-view-mock">
      <p>Editing: {filename}</p>
      <p>Type: {componentType}</p>
      <button onClick={onClose}>Close Editor</button>
    </div>
  )),
}));

const initialUIStoreState = useUIStore.getState();

// Helper to create a more complete mock Response
const createMockResponse = (body: any, ok: boolean, status: number = 200): Partial<Response> => ({
  ok,
  status,
  json: async () => body,
  text: async () => JSON.stringify(body), // Add text method for completeness
  headers: new Headers(),
  redirected: false,
  statusText: ok ? 'OK' : 'Error',
  type: 'default',
  url: '',
  clone: vi.fn(),
  body: null,
  bodyUsed: false,
  arrayBuffer: vi.fn(),
  blob: vi.fn(),
  formData: vi.fn(),
});


describe('ConfigListView', () => {
  beforeEach(() => {
    useUIStore.setState({
      ...initialUIStoreState,
      selectedComponent: 'agents', // Default for most tests
    });
    vi.mocked(apiClient).mockClear();
    // vi.spyOn(console, 'log').mockImplementation(() => {}); // No longer logging on select
    vi.mocked(ConfigEditorView).mockClear(); // Use vi.mocked without the cast
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should display loading state initially', async () => {
    vi.mocked(apiClient).mockReturnValue(new Promise(() => {})); // Keep it pending
    render(<ConfigListView />);
    expect(screen.getByText('Loading configuration files...')).toBeInTheDocument();
  });

  it('should fetch and display config files for the selected component type', async () => {
    const mockFiles = ['agent1.json', 'agent2.json'];
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse(mockFiles, true) as Response);

    render(<ConfigListView />);

    await waitFor(() => {
      expect(screen.getByText('agent1.json')).toBeInTheDocument();
      expect(screen.getByText('agent2.json')).toBeInTheDocument();
    });
    expect(apiClient).toHaveBeenCalledWith('/configs/agents');
    expect(screen.getByText('Agents Configurations')).toBeInTheDocument();
  });

  it('should display a message if no config files are found', async () => {
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse([], true) as Response);
    render(<ConfigListView />);
    await waitFor(() => {
      expect(screen.getByText('No configuration files found for agents.')).toBeInTheDocument();
    });
  });

  it('should display an error message if fetching fails', async () => {
    const errorDetail = 'Failed to fetch from server';
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse({ detail: errorDetail }, false, 400) as Response);
    render(<ConfigListView />);
    await waitFor(() => {
      expect(screen.getByText(`Error: ${errorDetail}`)).toBeInTheDocument();
    });
  });

  it('should handle network errors during fetch', async () => {
    vi.mocked(apiClient).mockRejectedValueOnce(new Error('Network problem'));
    render(<ConfigListView />);
    await waitFor(() => {
      expect(screen.getByText('Error: Network problem')).toBeInTheDocument();
    });
  });

  it('should render ConfigEditorView when a file is clicked and hide list', async () => {
    const mockFiles = ['test-agent.json'];
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse(mockFiles, true) as Response);
    render(<ConfigListView />);

    await waitFor(() => expect(screen.getByText('test-agent.json')).toBeInTheDocument());

    const fileButton = screen.getByRole('button', { name: 'test-agent.json' });
    await userEvent.click(fileButton);

    await waitFor(() => {
      expect(screen.getByTestId('config-editor-view-mock')).toBeInTheDocument();
      expect(screen.getByText('Editing: test-agent.json')).toBeInTheDocument(); // From mock
      expect(screen.getByText('Type: agents')).toBeInTheDocument(); // From mock
    });
    expect(screen.queryByText('Agents Configurations')).not.toBeInTheDocument(); // List title should be gone
    expect(screen.queryByText('test-agent.json')).not.toBeInTheDocument(); // File button should be gone
  });

  it('should return to list view when ConfigEditorView calls onClose', async () => {
    const mockFiles = ['test-agent.json'];
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse(mockFiles, true) as Response);
    render(<ConfigListView />);

    await waitFor(() => expect(screen.getByText('test-agent.json')).toBeInTheDocument());

    const fileButton = screen.getByRole('button', { name: 'test-agent.json' });
    await userEvent.click(fileButton);

    await waitFor(() => expect(screen.getByTestId('config-editor-view-mock')).toBeInTheDocument());

    const closeEditorButton = screen.getByRole('button', { name: 'Close Editor' }); // From mock
    await userEvent.click(closeEditorButton);

    await waitFor(() => {
      expect(screen.getByText('Agents Configurations')).toBeInTheDocument(); // List title should reappear
      expect(screen.getByText('test-agent.json')).toBeInTheDocument(); // File button should reappear
    });
    expect(screen.queryByTestId('config-editor-view-mock')).not.toBeInTheDocument();
  });


  it('should fetch configs for a different component type when uiStore changes and clear editor', async () => {
    // Initial fetch for agents
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse(['agent_config.json'], true) as Response);
    const { rerender } = render(<ConfigListView />);
    await waitFor(() => expect(apiClient).toHaveBeenCalledWith('/configs/agents'));

    // Click a file to show editor
    const fileButton = screen.getByRole('button', { name: 'agent_config.json' });
    await userEvent.click(fileButton);
    await waitFor(() => expect(screen.getByTestId('config-editor-view-mock')).toBeInTheDocument());


    // Change selected component in store
    vi.mocked(apiClient).mockClear();
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse(['client_config.json'], true) as Response);

    act(() => {
      useUIStore.setState({ selectedComponent: 'clients' });
    });
    rerender(<ConfigListView />); // Rerender to pick up store change effect

    await waitFor(() => expect(apiClient).toHaveBeenCalledWith('/configs/clients'));
    await waitFor(() => {
      expect(screen.getByText('client_config.json')).toBeInTheDocument();
      expect(screen.getByText('Clients Configurations')).toBeInTheDocument();
    });
    // Ensure editor is hidden
    expect(screen.queryByTestId('config-editor-view-mock')).not.toBeInTheDocument();
  });
});
