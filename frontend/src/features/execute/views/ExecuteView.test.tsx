/// <reference types="vitest/globals" />
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ExecuteView from './ExecuteView';
import apiClient from '../../../lib/apiClient';
import useUIStore from '../../../store/uiStore';

vi.mock('../../../lib/apiClient');
const initialUIStoreState = useUIStore.getState();

// Helper to create a more complete mock Response
const createMockResponse = (body: any, ok: boolean, status: number = 200): Partial<Response> => ({
  ok,
  status,
  json: async () => body,
  text: async () => JSON.stringify(body),
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

describe('ExecuteView', () => {
  beforeEach(() => {
    vi.mocked(apiClient).mockClear();
    useUIStore.setState(initialUIStoreState); // Reset store
    vi.spyOn(console, 'log').mockImplementation(() => {}); // Suppress console.log
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should display loading state initially', () => {
    vi.mocked(apiClient).mockImplementation(() => new Promise(() => {})); // Keep all calls pending
    render(<ExecuteView />);
    expect(screen.getByText('Loading executable components...')).toBeInTheDocument();
  });

  it('should fetch and display all types of executable components', async () => {
    const mockAgents = ['agent1', 'agent2'];
    const mockWorkflows = ['workflowA'];
    const mockCustomWorkflows = ['customWF1', 'customWF2'];

    vi.mocked(apiClient)
      .mockResolvedValueOnce(createMockResponse(mockAgents, true) as Response) // agents
      .mockResolvedValueOnce(createMockResponse(mockWorkflows, true) as Response) // workflows
      .mockResolvedValueOnce(createMockResponse(mockCustomWorkflows, true) as Response); // custom_workflows

    render(<ExecuteView />);

    await waitFor(() => {
      expect(screen.getByText('Agents')).toBeInTheDocument();
      expect(screen.getByText('agent1')).toBeInTheDocument();
      expect(screen.getByText('agent2')).toBeInTheDocument();

      expect(screen.getByText('Simple Workflows')).toBeInTheDocument();
      expect(screen.getByText('workflowA')).toBeInTheDocument();

      expect(screen.getByText('Custom Workflows')).toBeInTheDocument();
      expect(screen.getByText('customWF1')).toBeInTheDocument();
      expect(screen.getByText('customWF2')).toBeInTheDocument();
    });

    expect(apiClient).toHaveBeenCalledWith('/components/agents');
    expect(apiClient).toHaveBeenCalledWith('/components/workflows');
    expect(apiClient).toHaveBeenCalledWith('/components/custom_workflows');
  });

  it('should display an error message if any fetch fails', async () => {
    const fetchError = 'Network error fetching components';
    vi.mocked(apiClient)
      .mockResolvedValueOnce(createMockResponse([], true) as Response) // agents (ok)
      .mockRejectedValueOnce(new Error(fetchError)); // workflows (fail)
      // custom_workflows won't be called if previous fails due to Promise.all nature in component

    render(<ExecuteView />);
    await waitFor(() => {
      expect(screen.getByText(`Error: ${fetchError}`)).toBeInTheDocument();
    });
  });

  it('should display "No executable components found" if all lists are empty', async () => {
    vi.mocked(apiClient)
      .mockResolvedValueOnce(createMockResponse([], true) as Response)
      .mockResolvedValueOnce(createMockResponse([], true) as Response)
      .mockResolvedValueOnce(createMockResponse([], true) as Response);

    render(<ExecuteView />);
    await waitFor(() => {
      expect(screen.getByText('No executable components found.')).toBeInTheDocument();
    });
  });

  it('should select a component and update uiStore if type changes', async () => {
    const mockAgents = ['TestAgent'];
    vi.mocked(apiClient)
      .mockResolvedValueOnce(createMockResponse(mockAgents, true) as Response)
      .mockResolvedValueOnce(createMockResponse([], true) as Response)
      .mockResolvedValueOnce(createMockResponse([], true) as Response);

    // Set initial store state for selectedComponent to something different
    act(() => {
        useUIStore.setState({ selectedComponent: 'simple_workflows' });
    });

    render(<ExecuteView />);

    await waitFor(() => expect(screen.getByText('TestAgent')).toBeInTheDocument());

    const agentButton = screen.getByRole('button', { name: 'TestAgent' });
    await userEvent.click(agentButton);

    await waitFor(() => {
      expect(screen.getByText('Selected: TestAgent (agent)')).toBeInTheDocument();
    });

    // Check if uiStore.setSelectedComponent was called to update the component type
    expect(useUIStore.getState().selectedComponent).toBe('agents');
    expect(console.log).toHaveBeenCalledWith('Selected for execution:', { name: 'TestAgent', type: 'agent' });
  });

   it('should select a component and NOT update uiStore if type is the same', async () => {
    const mockAgents = ['TestAgentForSameType'];
    vi.mocked(apiClient)
      .mockResolvedValueOnce(createMockResponse(mockAgents, true) as Response)
      .mockResolvedValueOnce(createMockResponse([], true) as Response)
      .mockResolvedValueOnce(createMockResponse([], true) as Response);

    act(() => {
        useUIStore.setState({ selectedComponent: 'agents' }); // Already agents
    });
    const setSelectedComponentSpy = vi.spyOn(useUIStore.getState(), 'setSelectedComponent');


    render(<ExecuteView />);

    await waitFor(() => expect(screen.getByText('TestAgentForSameType')).toBeInTheDocument());

    const agentButton = screen.getByRole('button', { name: 'TestAgentForSameType' });
    await userEvent.click(agentButton);

    await waitFor(() => {
      expect(screen.getByText('Selected: TestAgentForSameType (agent)')).toBeInTheDocument();
    });

    expect(setSelectedComponentSpy).not.toHaveBeenCalled();
    setSelectedComponentSpy.mockRestore();
  });


  it('should not render a list section if its items are empty', async () => {
    const mockAgents = ['agentOnly'];
    vi.mocked(apiClient)
      .mockResolvedValueOnce(createMockResponse(mockAgents, true) as Response) // agents
      .mockResolvedValueOnce(createMockResponse([], true) as Response)       // workflows (empty)
      .mockResolvedValueOnce(createMockResponse([], true) as Response);      // custom_workflows (empty)

    render(<ExecuteView />);

    await waitFor(() => {
      expect(screen.getByText('Agents')).toBeInTheDocument();
      expect(screen.getByText('agentOnly')).toBeInTheDocument();
      expect(screen.queryByText('Simple Workflows')).not.toBeInTheDocument();
      expect(screen.queryByText('Custom Workflows')).not.toBeInTheDocument();
    });
  });

});
