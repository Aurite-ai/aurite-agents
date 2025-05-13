/// <reference types="vitest/globals" />
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'; // Added fireEvent
import userEvent from '@testing-library/user-event';
import ConfigEditorView from './ConfigEditorView';
import apiClient from '../../../lib/apiClient';
import type { ComponentType } from '../../../components/layout/ComponentSidebar'; // Changed to type import

vi.mock('../../../lib/apiClient');

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

describe('ConfigEditorView', () => {
  const mockOnClose = vi.fn();
  const componentType: ComponentType = 'agents';
  const filename = 'test-agent.json';

  beforeEach(() => {
    mockOnClose.mockClear();
    vi.mocked(apiClient).mockClear();
    // vi.spyOn(console, 'log').mockImplementation(() => {}); // console.log spy no longer needed for save
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should display loading state initially', () => {
    vi.mocked(apiClient).mockReturnValue(new Promise(() => {})); // Keep pending
    render(
      <ConfigEditorView
        componentType={componentType}
        filename={filename}
        onClose={mockOnClose}
      />
    );
    expect(screen.getByText('Loading editor...')).toBeInTheDocument();
  });

  it('should fetch and display config content in the editor', async () => {
    const mockContent = { key: 'value', nested: { num: 123 } };
    vi.mocked(apiClient).mockResolvedValueOnce(
      createMockResponse(mockContent, true) as Response
    );
    render(
      <ConfigEditorView
        componentType={componentType}
        filename={filename}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      // react-simple-code-editor renders its content inside a <textarea>
      const editorTextarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(JSON.parse(editorTextarea.value)).toEqual(mockContent);
    });
    expect(apiClient).toHaveBeenCalledWith(`/configs/${componentType}/${filename}`);
    expect(screen.getByText(`Editing: ${filename} (${componentType})`)).toBeInTheDocument();
  });

  it('should display an error message if fetching content fails', async () => {
    const errorDetail = 'File not found';
    vi.mocked(apiClient).mockResolvedValueOnce(
      createMockResponse({ detail: errorDetail }, false, 404) as Response
    );
    render(
      <ConfigEditorView
        componentType={componentType}
        filename={filename}
        onClose={mockOnClose}
      />
    );
    await waitFor(() => {
      // The component prepends "Initial Load Error: "
      expect(screen.getByText(`Initial Load Error: ${errorDetail}`)).toBeInTheDocument();
      // Check that editor shows error placeholder
      const editorTextarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(editorTextarea.value).toContain(`// Error loading ${filename}`);
    });
  });

  it('should handle network error when fetching content', async () => {
    vi.mocked(apiClient).mockRejectedValueOnce(new Error('Network Error'));
     render(
      <ConfigEditorView
        componentType={componentType}
        filename={filename}
        onClose={mockOnClose}
      />
    );
    await waitFor(() => {
      // The component prepends "Initial Load Error: "
      expect(screen.getByText('Initial Load Error: Network Error')).toBeInTheDocument();
    });
  });

  it('should update code state on editor change', async () => {
    const mockContent = { initial: 'data' };
    vi.mocked(apiClient).mockResolvedValueOnce(
      createMockResponse(mockContent, true) as Response
    );
    render(
      <ConfigEditorView
        componentType={componentType}
        filename={filename}
        onClose={mockOnClose}
      />
    );

    let editorTextarea: HTMLTextAreaElement;
    await waitFor(() => {
      editorTextarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(JSON.parse(editorTextarea.value)).toEqual(mockContent);
    });

    const newCode = JSON.stringify({ updated: 'data' }, null, 2);
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    fireEvent.change(editorTextarea!, { target: { value: newCode } });

    await waitFor(() => {
        // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
        expect(editorTextarea!.value).toBe(newCode);
    });
  });

  it('should call onClose when "Back to List" button is clicked', async () => {
    vi.mocked(apiClient).mockResolvedValueOnce(
      createMockResponse({ key: 'data' }, true) as Response
    );
    render(
      <ConfigEditorView
        componentType={componentType}
        filename={filename}
        onClose={mockOnClose}
      />
    );
    await waitFor(() => screen.getByText('Back to List')); // Ensure it's rendered

    const backButton = screen.getByRole('button', { name: 'Back to List' });
    await userEvent.click(backButton);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('should successfully save valid JSON content', async () => {
    const initialContent = { message: 'hello' };
    const newContent = { message: 'hello world', updated: true };
    const newCode = JSON.stringify(newContent, null, 2);

    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse(initialContent, true) as Response); // For initial load
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse({}, true, 200) as Response); // For PUT save

    render(
      <ConfigEditorView componentType={componentType} filename={filename} onClose={mockOnClose} />
    );

    let editorTextarea: HTMLTextAreaElement;
    await waitFor(() => {
      editorTextarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(JSON.parse(editorTextarea.value)).toEqual(initialContent);
    });

    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    fireEvent.change(editorTextarea!, { target: { value: newCode } });

    const saveButton = screen.getByRole('button', { name: 'Save Configuration' });
    await userEvent.click(saveButton);

    await waitFor(() => {
      expect(apiClient).toHaveBeenCalledWith(
        `/configs/${componentType}/${filename}`,
        expect.objectContaining({
          method: 'PUT',
          body: { content: newContent }, // apiClient receives an object, it stringifies internally
        })
      );
    });
    expect(screen.getByText('Configuration saved successfully!')).toBeInTheDocument();
  });

  it('should display an error if saving fails due to API error', async () => {
    const initialContent = { message: 'hello' };
    const saveErrorDetail = 'Server failed to save';
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse(initialContent, true) as Response); // Initial load
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse({ detail: saveErrorDetail }, false, 500) as Response); // Save fails

    render(
      <ConfigEditorView componentType={componentType} filename={filename} onClose={mockOnClose} />
    );
    await waitFor(() => screen.getByRole('textbox')); // Wait for editor to load

    const saveButton = screen.getByRole('button', { name: 'Save Configuration' });
    await userEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(saveErrorDetail)).toBeInTheDocument();
    });
  });

  it('should display an error if content is not valid JSON on save', async () => {
    const initialContent = { message: 'hello' };
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse(initialContent, true) as Response); // Initial load

    render(
      <ConfigEditorView componentType={componentType} filename={filename} onClose={mockOnClose} />
    );

    let editorTextarea: HTMLTextAreaElement;
    await waitFor(() => {
      editorTextarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    });

    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    fireEvent.change(editorTextarea!, { target: { value: 'this is not json' } });

    const saveButton = screen.getByRole('button', { name: 'Save Configuration' });
    await userEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Invalid JSON format. Please correct and try again.')).toBeInTheDocument();
    });
    expect(apiClient).toHaveBeenCalledTimes(1); // Only initial fetch, no PUT call
  });

  it('should show "Saving..." text and disable button while saving', async () => {
    const initialContent = { message: 'hello' };
    vi.mocked(apiClient).mockResolvedValueOnce(createMockResponse(initialContent, true) as Response); // Initial load
    // Make save call pend
    vi.mocked(apiClient).mockImplementationOnce(() => new Promise(() => {}));


    render(
      <ConfigEditorView componentType={componentType} filename={filename} onClose={mockOnClose} />
    );
    await waitFor(() => screen.getByRole('textbox'));

    const saveButton = screen.getByRole('button', { name: 'Save Configuration' });
    // No await here, we want to check state during the save
    userEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Saving...' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Saving...' })).toBeDisabled();
    });
  });

});
