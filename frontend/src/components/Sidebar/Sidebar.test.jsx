import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Sidebar from './Sidebar';

const now = new Date();
const yesterday = new Date();
yesterday.setDate(now.getDate() - 1);

const traces = [
  {
    trace_id: 'trace-1',
    name: 'Today flow',
    framework: 'multi-test',
    status: 'success',
    start_time: now.toISOString(),
    duration_ms: 1200,
    total_tokens: 120,
    total_cost_usd: 0.0002,
    agent_count: 2,
    tool_calls: 3,
    llm_calls: 1,
  },
  {
    trace_id: 'trace-2',
    name: 'Yesterday flow',
    framework: 'multi-test',
    status: 'error',
    start_time: yesterday.toISOString(),
    duration_ms: 900,
    total_tokens: 90,
    total_cost_usd: 0.0001,
    agent_count: 1,
    tool_calls: 1,
    llm_calls: 1,
  },
];

const baseProps = {
  traces: [],
  selectedTraceId: null,
  onSelectTrace: () => {},
  onDeleteTrace: () => {},
  onExportTrace: () => {},
  loading: false,
  isConnected: true,
  errorCode: null,
  errorMessage: '',
  lastFetchAt: null,
  onRetry: () => {},
  density: 'comfortable',
  groupBy: 'date',
  defaultFiltersOpen: false,
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
    expect(screen.getByText(/Session expired or unauthorized/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('groups traces by date buckets and shows all trace names', () => {
    render(<Sidebar {...baseProps} traces={traces} />);

    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('Yesterday')).toBeInTheDocument();
    expect(screen.getByText('Today flow')).toBeInTheDocument();
    expect(screen.getByText('Yesterday flow')).toBeInTheDocument();
  });

  it('calls onDensityChange when compact mode is selected', () => {
    const onDensityChange = vi.fn();
    render(<Sidebar {...baseProps} traces={traces} onDensityChange={onDensityChange} />);

    fireEvent.click(screen.getByRole('button', { name: /compact/i }));
    expect(onDensityChange).toHaveBeenCalledWith('compact');
  });
});
