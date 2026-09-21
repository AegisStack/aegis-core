/**
 * Tests for MetricCard.
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MetricCard } from '../MetricCard'
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

describe('MetricCard', () => {
  beforeEach(() => {
    push.mockClear()
  })

  it('renders the title, formatted value, and subtitle', () => {
    render(
      <MetricCard
        title="Total Calls"
        value={1234}
        subtitle="Last 7 days"
        color="text-foreground"
        sparklineData={[]}
        sparklineKey="total"
      />
    )

    expect(screen.getByText('Total Calls')).toBeInTheDocument()
    expect(screen.getByText('1,234')).toBeInTheDocument()
    expect(screen.getByText('Last 7 days')).toBeInTheDocument()
  })

  it('does not render a sparkline with fewer than 2 data points', () => {
    const { container } = render(
      <MetricCard
        title="Allowed"
        value={5}
        subtitle="subtitle"
        color="text-green-600"
        sparklineData={[bucket()]}
        sparklineKey="allows"
      />
    )
    expect(container.querySelector('.recharts-responsive-container')).not.toBeInTheDocument()
  })

  it('navigates to /explore with the drill-down outcome and time range on click', async () => {
    const user = userEvent.setup()
    render(
      <MetricCard
        title="Denied"
        value={3}
        subtitle="subtitle"
        color="text-red-600"
        sparklineData={[]}
        sparklineKey="denies"
        drillDownOutcome="deny"
        startTime="2024-01-15T00:00:00Z"
        endTime="2024-01-15T01:00:00Z"
      />
    )

    await user.click(screen.getByText('Denied'))

    expect(push).toHaveBeenCalledTimes(1)
    const url = push.mock.calls[0][0] as string
    expect(url.startsWith('/explore?')).toBe(true)
    const params = new URLSearchParams(url.split('?')[1])
    expect(params.get('outcome')).toBe('deny')
    expect(params.get('start')).toBe('2024-01-15T00:00:00Z')
    expect(params.get('end')).toBe('2024-01-15T01:00:00Z')
  })

  it('does not navigate on click when there is nothing to drill down to', async () => {
    const user = userEvent.setup()
    render(
      <MetricCard
        title="Total Calls"
        value={10}
        subtitle="subtitle"
        color="text-foreground"
        sparklineData={[]}
        sparklineKey="total"
      />
    )

    await user.click(screen.getByText('Total Calls'))
    expect(push).not.toHaveBeenCalled()
  })
})
