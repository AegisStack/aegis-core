/**
 * Tests for ThroughputChart / LatencyChart.
 *
 * Kept to what's reliably testable under jsdom without a real layout
 * engine: the loading/empty presentational states (pure conditionals) and
 * navigation on click, not recharts' actual pixel rendering or the
 * drag-to-zoom pixel math (which needs real getBoundingClientRect sizing
 * this environment can't provide).
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThroughputChart, LatencyChart } from '../TimeSeriesChart'
import type { TimeseriesBucket } from '@/lib/api'

const push = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}))

function bucket(overrides: Partial<TimeseriesBucket> = {}): TimeseriesBucket {
  return {
    time: '2024-01-15T10:00:00Z',
    total: 10,
    allows: 8,
    denies: 1,
    escalations: 1,
    avg_latency: 5,
    p95_latency: 10,
    p99_latency: 15,
    ...overrides,
  }
}

describe('ThroughputChart', () => {
  beforeEach(() => push.mockClear())

  it('shows a loading skeleton when isLoading is true', () => {
    const { container } = render(<ThroughputChart data={[]} interval="1m" isLoading />)
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('shows an empty state with a working "Open Log Explorer" link when there is no data', async () => {
    const user = userEvent.setup()
    render(
      <ThroughputChart
        data={[]}
        interval="1m"
        rangeStart="2024-01-15T09:00:00Z"
        rangeEnd="2024-01-15T10:00:00Z"
      />
    )

    expect(screen.getByText('No data for this time range')).toBeInTheDocument()

    await user.click(screen.getByText('Open Log Explorer'))
    expect(push).toHaveBeenCalledTimes(1)
    const url = push.mock.calls[0][0] as string
    const params = new URLSearchParams(url.split('?')[1])
    expect(params.get('start')).toBe('2024-01-15T09:00:00Z')
    expect(params.get('end')).toBe('2024-01-15T10:00:00Z')
  })

  it('navigates to the Log Explorer via the panel header link', async () => {
    const user = userEvent.setup()
    render(<ThroughputChart data={[bucket()]} interval="1m" />)

    await user.click(screen.getByText('Log Explorer'))
    expect(push).toHaveBeenCalledTimes(1)
  })

  it('renders the panel title and subtitle', () => {
    render(<ThroughputChart data={[bucket()]} interval="5m" />)
    expect(screen.getByText('Throughput')).toBeInTheDocument()
    expect(screen.getByText(/Stacked outcomes per 5m/)).toBeInTheDocument()
  })
})

describe('LatencyChart', () => {
  beforeEach(() => push.mockClear())

  it('shows a loading skeleton when isLoading is true', () => {
    const { container } = render(<LatencyChart data={[]} interval="1m" isLoading />)
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('shows an empty state when there is no data', () => {
    render(<LatencyChart data={[]} interval="1m" />)
    expect(screen.getByText('No data for this time range')).toBeInTheDocument()
  })

  it('renders the panel title', () => {
    render(<LatencyChart data={[bucket()]} interval="1h" />)
    expect(screen.getByText('Latency')).toBeInTheDocument()
    expect(screen.getByText(/Avg \/ P95 \/ P99 per 1h/)).toBeInTheDocument()
  })
})
