import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Layout from './Layout';
import useUIStore from '../../store/uiStore';
import type { ActionType } from './ActionTabs';
import type { ComponentType } from './ComponentSidebar';

// Mock child components to simplify Layout testing and focus on its own logic
vi.mock('./TopNavbar', () => ({
  default: () => <div data-testid="top-navbar-mock">TopNavbar Mock</div>,
}));
vi.mock('./ActionTabs', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  default: ({ selectedAction, onSelectAction }: any) => (
    <div data-testid="action-tabs-mock">
      <span>Selected Action: {selectedAction}</span>
      <button onClick={() => onSelectAction('execute' as ActionType)}>Select Execute Action</button>
    </div>
  ),
}));
vi.mock('./ComponentSidebar', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  default: ({ selectedComponent, onSelectComponent }: any) => (
    <div data-testid="component-sidebar-mock">
      <span>Selected Component: {selectedComponent}</span>
      <button onClick={() => onSelectComponent('clients' as ComponentType)}>Select Clients Component</button>
    </div>
  ),
}));

const initialUIStoreState = useUIStore.getState();

describe('Layout', () => {
  beforeEach(() => {
    // Reset UI store to its initial state
    useUIStore.setState(initialUIStoreState);
    // It's good practice to also reset any mocks if they have state or call counts
    // For this test, child component mocks are simple, but if they had internal vi.fn(), reset them.
  });

  it('should render TopNavbar, ActionTabs, and ComponentSidebar', () => {
    render(<Layout />);
    expect(screen.getByTestId('top-navbar-mock')).toBeInTheDocument();
    expect(screen.getByTestId('action-tabs-mock')).toBeInTheDocument();
    expect(screen.getByTestId('component-sidebar-mock')).toBeInTheDocument();
  });

  // Removed the 'should render children content' test as Layout now manages its own content

  it('should pass selectedAction from uiStore to ActionTabs and update store on selection', async () => {
    // Set initial store state for the test
    act(() => {
      useUIStore.setState({ selectedAction: 'build' });
    });

    render(<Layout />);

    // Check if ActionTabs mock receives the initial selectedAction
    expect(screen.getByText('Selected Action: build')).toBeInTheDocument();

    // Simulate ActionTabs calling onSelectAction (via its mock)
    const selectExecuteButton = screen.getByRole('button', { name: 'Select Execute Action' });
    await userEvent.click(selectExecuteButton);

    // Check if uiStore was updated
    expect(useUIStore.getState().selectedAction).toBe('execute');
  });

  it('should pass selectedComponent from uiStore to ComponentSidebar and update store on selection', async () => {
    // Set initial store state for the test
    act(() => {
      useUIStore.setState({ selectedComponent: 'agents' });
    });

    render(<Layout />);

    // Check if ComponentSidebar mock receives the initial selectedComponent
    expect(screen.getByText('Selected Component: agents')).toBeInTheDocument();

    // Simulate ComponentSidebar calling onSelectComponent (via its mock)
    const selectClientsButton = screen.getByRole('button', { name: 'Select Clients Component' });
    await userEvent.click(selectClientsButton);

    // Check if uiStore was updated
    expect(useUIStore.getState().selectedComponent).toBe('clients');
  });

  it('should display the selected action and component from the store in its placeholder area', () => {
    act(() => {
      useUIStore.setState({ selectedAction: 'evaluate', selectedComponent: 'custom_workflows' });
    });
    render(<Layout />);

    expect(screen.getByText('Selected Action:')).toBeInTheDocument();
    expect(screen.getByText('evaluate')).toBeInTheDocument(); // Check for the value itself
    expect(screen.getByText('Selected Component:')).toBeInTheDocument();
    expect(screen.getByText('custom_workflows')).toBeInTheDocument(); // Check for the value itself
  });
});
