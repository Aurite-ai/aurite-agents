import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ApiKeyModal from './ApiKeyModal';
import useAuthStore from '../../store/authStore'; // Adjust path as necessary

// Mock the auth store
const mockValidateApiKey = vi.fn();
const mockClearAuth = vi.fn(); // Though not directly used by modal, good practice if store is complex
const mockSetApiKey = vi.fn();

const initialStoreState = useAuthStore.getState();

describe('ApiKeyModal', () => {
  beforeEach(() => {
    // Reset store state and mock implementations before each test
    useAuthStore.setState({
      ...initialStoreState, // Reset to actual initial state from store definition
      apiKey: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      // Overwrite actions with mocks for this test suite
      validateApiKey: mockValidateApiKey,
      clearAuth: mockClearAuth,
      setApiKey: mockSetApiKey,
    });
    mockValidateApiKey.mockClear();
    mockClearAuth.mockClear();
    mockSetApiKey.mockClear();
  });

  it('should not render if authenticated', () => {
    act(() => {
      useAuthStore.setState({ isAuthenticated: true });
    });
    const { container } = render(<ApiKeyModal />);
    expect(container.firstChild).toBeNull();
  });

  it('should render the modal if not authenticated', () => {
    act(() => {
      useAuthStore.setState({ isAuthenticated: false });
    });
    render(<ApiKeyModal />);
    expect(screen.getByText('Enter API Key')).toBeInTheDocument();
    expect(screen.getByLabelText('API Key')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument();
  });

  it('should update input value on change', async () => {
    act(() => {
      useAuthStore.setState({ isAuthenticated: false });
    });
    render(<ApiKeyModal />);
    const input = screen.getByLabelText('API Key') as HTMLInputElement;
    await userEvent.type(input, 'test-key');
    expect(input.value).toBe('test-key');
  });

  it('should call validateApiKey on form submission with the entered key', async () => {
    mockValidateApiKey.mockResolvedValue(true); // Simulate successful validation
    act(() => {
      useAuthStore.setState({ isAuthenticated: false });
    });
    render(<ApiKeyModal />);
    const input = screen.getByLabelText('API Key');
    const submitButton = screen.getByRole('button', { name: 'Submit' });

    await userEvent.type(input, 'test-key-123');
    await userEvent.click(submitButton);

    expect(mockValidateApiKey).toHaveBeenCalledTimes(1);
    expect(mockValidateApiKey).toHaveBeenCalledWith('test-key-123');
  });

  it('should display loading state when isLoading is true', () => {
    act(() => {
      useAuthStore.setState({ isAuthenticated: false, isLoading: true });
    });
    render(<ApiKeyModal />);
    expect(screen.getByRole('button', { name: 'Validating...' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Validating...' })).toBeDisabled();
    expect(screen.getByLabelText('API Key')).toBeDisabled();
  });

  it('should display error message when error is present', () => {
    const errorMessage = 'Invalid key provided.';
    act(() => {
      useAuthStore.setState({ isAuthenticated: false, error: errorMessage });
    });
    render(<ApiKeyModal />);
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('should not call validateApiKey if input is empty or whitespace', async () => {
    act(() => {
      useAuthStore.setState({ isAuthenticated: false });
    });
    render(<ApiKeyModal />);
    const submitButton = screen.getByRole('button', { name: 'Submit' });

    // Test with empty input
    await userEvent.click(submitButton);
    expect(mockValidateApiKey).not.toHaveBeenCalled();

    // Test with whitespace input
    const input = screen.getByLabelText('API Key');
    await userEvent.type(input, '   ');
    await userEvent.click(submitButton);
    expect(mockValidateApiKey).not.toHaveBeenCalled();
  });
});
