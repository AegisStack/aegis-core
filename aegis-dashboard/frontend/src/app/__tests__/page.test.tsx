/**
 * Tests for the overview dashboard page.
 *
 * LiveFeed and the recharts-based TimeSeriesChart panels are stubbed:
 * both have their own dedicated test files, and stubbing them keeps this
 * test focused on the page's own composition (metric cards, denied-rules
 * list, loading state) instead of their internals.
 */

import { screen } from '@testing-library/react'
import { renderWithProviders } from '@/test-utils'
import DashboardPage from '../page'
import { api } from '@/lib/api'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}))

jest.mock('@/components/LiveFeed', () => ({
  LiveFeed: () => <div data-testid="live-feed-stub" />,
}))

jest.mock('@/components/TimeSeriesChart', () => ({
  ThroughputChart: () => <div data-testid="throughput-chart-stub" />,
  LatencyChart: () => <div data-testid="latency-chart-stub" />,
}))

jest.mock('@/lib/api', () => ({
  api: {
    getMetricsSummary: jest.fn(),
    getTimeseries: jest.fn(),
  },
}))

function mockMetrics(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    total_calls: 100,
    allows: 80,
    denies: 15,
    escalations: 5,
    top_tools: [{ tool: 'issue_refund', count: 50, deny_rate: 0.1 }],
    top_denied_rules: [{ rule: 'amount_exceeds_limit', count: 7 }],
    latency: { avg: 12.34, max: 99.9 },
    ...overrides,
  }
}

describe('DashboardPage (overview)', () => {
  beforeEach(() => {
    ;(api.getMetricsSummary as jest.Mock).mockResolvedValue(mockMetrics())
    ;(api.getTimeseries as jest.Mock).mockResolvedValue({ interval: '1m', buckets: [] })
  })

  it('shows a loading state before metrics resolve', () => {
    ;(api.getMetricsSummary as jest.Mock).mockReturnValue(new Promise(() => {}))
    renderWithProviders(<DashboardPage />)
    expect(screen.getByText('Loading dashboard...')).toBeInTheDocument()
  })

  it('fetches metrics scoped to the current customer', () => {
    renderWithProviders(<DashboardPage />, { customerId: 'beta-corp' })
    expect(api.getMetricsSummary).toHaveBeenCalledWith({ customer_id: 'beta-corp', period: '7d' })
  })

  it('renders the metric card values once loaded', async () => {
    renderWithProviders(<DashboardPage />)

    expect(await screen.findByText('100')).toBeInTheDocument() // total calls
    expect(screen.getByText('80')).toBeInTheDocument() // allowed
    expect(screen.getByText('15')).toBeInTheDocument() // denied
    expect(screen.getByText('5')).toBeInTheDocument() // escalations
  })

  it('renders the top denied rules list', async () => {
    renderWithProviders(<DashboardPage />)
    expect(await screen.findByText('amount_exceeds_limit')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('shows an empty message when there are no denied rules', async () => {
    ;(api.getMetricsSummary as jest.Mock).mockResolvedValue(
      mockMetrics({ top_denied_rules: [] })
    )
    renderWithProviders(<DashboardPage />)
    expect(await screen.findByText('No denied rules in this period')).toBeInTheDocument()
  })

  it('renders latency stats', async () => {
    renderWithProviders(<DashboardPage />)
    expect(await screen.findByText('12.34ms')).toBeInTheDocument()
    expect(screen.getByText('99.90ms')).toBeInTheDocument()
  })

  it('renders the stubbed chart panels and live feed', async () => {
    renderWithProviders(<DashboardPage />)
    expect(await screen.findByTestId('throughput-chart-stub')).toBeInTheDocument()
    expect(screen.getByTestId('latency-chart-stub')).toBeInTheDocument()
    expect(screen.getByTestId('live-feed-stub')).toBeInTheDocument()
  })
})
