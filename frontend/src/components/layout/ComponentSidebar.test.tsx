import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ComponentSidebar, { type SelectedSidebarItemType as ComponentType } from './ComponentSidebar';
import useUIStore from '../../store/uiStore'; // Import the store

// Mock the uiStore
vi.mock('../../store/uiStore');

describe('ComponentSidebar', () => {
  const mockSetSelectedComponent = vi.fn();

  const componentsToTest: { id: ComponentType; label: string }[] = [
    { id: 'clients', label: 'Clients' },
    { id: 'agents', label: 'Agents' },
    { id: 'simple_workflows', label: 'Simple Workflows' },
    { id: 'custom_workflows', label: 'Custom Workflows' },
    // 'projects' is also a valid SelectedSidebarItemType but handled separately in UI
  ];

  beforeEach(() => {
    mockSetSelectedComponent.mockClear();
    // Default mock implementation for useUIStore
    (useUIStore as vi.Mock).mockReturnValue({
      selectedComponent: 'agents', // Default selected component for tests
      setSelectedComponent: mockSetSelectedComponent,
      // Add other state/actions from useUIStore if ComponentSidebar uses them
    });
  });

  it('should render the title "Component Types"', () => {
    render(<ComponentSidebar />);
    expect(screen.getByText('Component Types')).toBeInTheDocument();
  });

  it('should render all component type buttons and project management button', () => {
    render(<ComponentSidebar />);
    componentsToTest.forEach(component => {
      expect(screen.getByRole('button', { name: component.label })).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'Active Project Files' })).toBeInTheDocument();
  });

  it('should highlight the selected component button based on store state', () => {
    (useUIStore as vi.Mock).mockReturnValue({
      selectedComponent: 'simple_workflows',
      setSelectedComponent: mockSetSelectedComponent,
    });
    render(<ComponentSidebar />);

    const selectedButton = screen.getByRole('button', { name: 'Simple Workflows' });
    expect(selectedButton).toHaveClass('bg-dracula-purple');
    expect(selectedButton).toHaveClass('text-dracula-foreground');

    const nonSelectedButton = screen.getByRole('button', { name: 'Agents' });
    expect(nonSelectedButton).not.toHaveClass('bg-dracula-purple');
  });

  it('should highlight the project management button when selected in store state', () => {
    (useUIStore as vi.Mock).mockReturnValue({
      selectedComponent: 'projects',
      setSelectedComponent: mockSetSelectedComponent,
    });
    render(<ComponentSidebar />);
    const projectButton = screen.getByRole('button', { name: 'Active Project Files' });
    expect(projectButton).toHaveClass('bg-dracula-green'); // Specific highlight for project
  });

  it('should call setSelectedComponent from store with the correct component id when a button is clicked', async () => {
    render(<ComponentSidebar />);

    const clientsButton = screen.getByRole('button', { name: 'Clients' });
    await userEvent.click(clientsButton);
    expect(mockSetSelectedComponent).toHaveBeenCalledTimes(1);
    expect(mockSetSelectedComponent).toHaveBeenCalledWith('clients');

    const customWorkflowsButton = screen.getByRole('button', { name: 'Custom Workflows' });
    await userEvent.click(customWorkflowsButton);
    expect(mockSetSelectedComponent).toHaveBeenCalledTimes(2);
    expect(mockSetSelectedComponent).toHaveBeenCalledWith('custom_workflows');

    const projectButton = screen.getByRole('button', { name: 'Active Project Files' });
    await userEvent.click(projectButton);
    expect(mockSetSelectedComponent).toHaveBeenCalledTimes(3);
    expect(mockSetSelectedComponent).toHaveBeenCalledWith('projects');
  });
});
