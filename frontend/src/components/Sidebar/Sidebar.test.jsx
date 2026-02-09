import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Sidebar from './Sidebar';

const baseProps = {
  traces: [],
  selectedTraceId: null,
  onSelectTrace: () => {},
  onDeleteTrace: () => {},
  loading: false,
  isConnected: true,
  errorCode: null,
  errorMessage: '',
  lastFetchAt: null,
  onRetry: () => {},
};

describe('Sidebar', () => {
  it('renders empty state when no traces exist and no errors are present', () => {
    render(<Sidebar {...baseProps} />);

    expect(screen.getByText('No traces yet')).toBeInTheDocument();
  });

  it('renders auth-specific hint and allows retry action', () => {
    const onRetry = vi.fn();

    render(
      <Sidebar
        {...baseProps}
        errorCode={401}
        errorMessage="Invalid API key"
        onRetry={onRetry}
      />
    );

    expect(screen.getByText('Could not load traces')).toBeInTheDocument();
    expect(
      screen.getByText(/Session expired or unauthorized/i)
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
