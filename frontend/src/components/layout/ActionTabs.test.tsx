import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ActionTabs, { type ActionType } from './ActionTabs';

describe('ActionTabs', () => {
  const mockOnSelectAction = vi.fn();

  const actionsToTest: { id: ActionType; label: string }[] = [
    { id: 'build', label: 'Build' },
    { id: 'configure', label: 'Configure' },
    { id: 'execute', label: 'Execute' },
    { id: 'evaluate', label: 'Evaluate' },
  ];

  beforeEach(() => {
    mockOnSelectAction.mockClear();
  });

  it('should render all action tabs', () => {
    render(<ActionTabs selectedAction="build" onSelectAction={mockOnSelectAction} />);
    actionsToTest.forEach(action => {
      expect(screen.getByRole('button', { name: action.label })).toBeInTheDocument();
    });
  });

  it('should highlight the selected action tab', () => {
    const selected: ActionType = 'configure';
    render(<ActionTabs selectedAction={selected} onSelectAction={mockOnSelectAction} />);

    const selectedButton = screen.getByRole('button', { name: 'Configure' });
    // Check for classes that indicate active state
    expect(selectedButton).toHaveClass('border-dracula-pink');
    expect(selectedButton).toHaveClass('text-dracula-pink');

    const nonSelectedButton = screen.getByRole('button', { name: 'Build' });
    expect(nonSelectedButton).not.toHaveClass('border-dracula-pink');
    expect(nonSelectedButton).not.toHaveClass('text-dracula-pink');
    expect(nonSelectedButton).toHaveClass('text-dracula-comment'); // Check for default non-active text color
  });

  it('should call onSelectAction with the correct action id when a tab is clicked', async () => {
    render(<ActionTabs selectedAction="build" onSelectAction={mockOnSelectAction} />);

    const configureButton = screen.getByRole('button', { name: 'Configure' });
    await userEvent.click(configureButton);
    expect(mockOnSelectAction).toHaveBeenCalledTimes(1);
    expect(mockOnSelectAction).toHaveBeenCalledWith('configure');

    const executeButton = screen.getByRole('button', { name: 'Execute' });
    await userEvent.click(executeButton);
    expect(mockOnSelectAction).toHaveBeenCalledTimes(2);
    expect(mockOnSelectAction).toHaveBeenCalledWith('execute');
  });
});
