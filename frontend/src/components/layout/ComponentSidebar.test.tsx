import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ComponentSidebar, { type ComponentType } from './ComponentSidebar';

describe('ComponentSidebar', () => {
  const mockOnSelectComponent = vi.fn();

  const componentsToTest: { id: ComponentType; label: string }[] = [
    { id: 'clients', label: 'Clients' },
    { id: 'agents', label: 'Agents' },
    { id: 'simple_workflows', label: 'Simple Workflows' },
    { id: 'custom_workflows', label: 'Custom Workflows' },
  ];

  beforeEach(() => {
    mockOnSelectComponent.mockClear();
  });

  it('should render the title "Component Types"', () => {
    render(<ComponentSidebar selectedComponent="agents" onSelectComponent={mockOnSelectComponent} />);
    expect(screen.getByText('Component Types')).toBeInTheDocument();
  });

  it('should render all component type buttons', () => {
    render(<ComponentSidebar selectedComponent="agents" onSelectComponent={mockOnSelectComponent} />);
    componentsToTest.forEach(component => {
      expect(screen.getByRole('button', { name: component.label })).toBeInTheDocument();
    });
  });

  it('should highlight the selected component button', () => {
    const selected: ComponentType = 'simple_workflows';
    render(<ComponentSidebar selectedComponent={selected} onSelectComponent={mockOnSelectComponent} />);

    const selectedButton = screen.getByRole('button', { name: 'Simple Workflows' });
    // Check for classes that indicate active state
    expect(selectedButton).toHaveClass('bg-dracula-purple');
    expect(selectedButton).toHaveClass('text-dracula-foreground');

    const nonSelectedButton = screen.getByRole('button', { name: 'Agents' });
    expect(nonSelectedButton).not.toHaveClass('bg-dracula-purple');
    expect(nonSelectedButton).toHaveClass('text-dracula-foreground'); // Non-selected items also use foreground text
  });

  it('should call onSelectComponent with the correct component id when a button is clicked', async () => {
    render(<ComponentSidebar selectedComponent="agents" onSelectComponent={mockOnSelectComponent} />);

    const clientsButton = screen.getByRole('button', { name: 'Clients' });
    await userEvent.click(clientsButton);
    expect(mockOnSelectComponent).toHaveBeenCalledTimes(1);
    expect(mockOnSelectComponent).toHaveBeenCalledWith('clients');

    const customWorkflowsButton = screen.getByRole('button', { name: 'Custom Workflows' });
    await userEvent.click(customWorkflowsButton);
    expect(mockOnSelectComponent).toHaveBeenCalledTimes(2);
    expect(mockOnSelectComponent).toHaveBeenCalledWith('custom_workflows');
  });
});
