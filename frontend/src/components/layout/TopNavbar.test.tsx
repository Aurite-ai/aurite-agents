import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TopNavbar from './TopNavbar';

describe('TopNavbar', () => {
  it('should render the title "Aurite AI Studio"', () => {
    render(<TopNavbar />);
    expect(screen.getByText('Aurite AI Studio')).toBeInTheDocument();
  });

  it('should render a placeholder for the company logo', () => {
    render(<TopNavbar />);
    // Assuming the placeholder is a div with text 'A' for now
    expect(screen.getByText('A')).toBeInTheDocument();
  });

  it('should render a placeholder for the user profile icon', () => {
    render(<TopNavbar />);
    // Check for the SVG by its path data or a more specific role/test-id if added
    // For now, we can check if an svg element is present.
    const svgElement = screen.getByRole('navigation').querySelector('svg'); // More robust selector might be needed
    expect(svgElement).toBeInTheDocument();
  });
});
