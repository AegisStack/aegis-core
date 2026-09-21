/**
 * Tests for the Log Explorer page.
 *
 * TimeSeriesChart panels are stubbed (covered by their own test file);
 * this focuses on the page's own data composition: summary stats, the
 * agent/tool breakdown tables, and the audit record list.
 */

import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test-utils'
import ExplorePage from '../page'
import { api, type AuditRecord } from '@/lib/api'

const routerBack = jest.fn()
const routerPush = jest.fn()
let searchParams = new URLSearchParams()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ back: routerBack, push: routerPush }),
  useSearchParams: () => searchParams,
}))

jest.mock('@/components/TimeSeriesChart', () => ({
  ThroughputChart: () => <div data-testid="throughput-chart-stub" />,
  LatencyChart: () => <div data-testid="latency-chart-stub" />,
}))

jest.mock('@/lib/api', () => ({
  api: {
    getExplore: jest.fn(),
    getTimeseries: jest.fn(),
    getAuditRecords: jest.fn(),
  },
}))

function explore(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    window: { start: '', end: '', outcome_filter: null },
    summary: {
      total: 42,
      allows: 30,
      denies: 10,
      escalations: 2,
      avg_latency: 5.5,
      p95_latency: 12.1,
      p99_latency: 20.4,
    },
    agents: [{ agent_id: 'billing-agent', total: 77, allows: 70, denies: 7, escalations: 0, deny_rate: 0.16, avg_latency: 4.2 }],
    tools: [{ tool_name: 'issue_refund', total: 88, allows: 80, denies: 8, escalations: 0, deny_rate: 0.25, avg_latency: 3.1 }],
    ...overrides,
  }
}

function record(overrides: Partial<AuditRecord> = {}): AuditRecord {
  return {
    record_id: 'rec-1',
    timestamp: new Date().toISOString(),
    agent_id: 'billing-agent',
    policy_version: 'v1',
    tool_name: 'issue_refund',
    params: { amount_usd: 500 },
    outcome: 'deny',
    matched_rule: 'amount_exceeds_limit',
    reason: 'Amount exceeds limit',
    ...overrides,
  }
}

describe('ExplorePage', () => {
  beforeEach(() => {
    searchParams = new URLSearchParams()
    routerBack.mockClear()
    routerPush.mockClear()
    ;(api.getExplore as jest.Mock).mockReset().mockResolvedValue(explore())
    ;(api.getTimeseries as jest.Mock).mockReset().mockResolvedValue({ interval: '1m', buckets: [] })
    ;(api.getAuditRecords as jest.Mock).mockReset().mockResolvedValue([])
  })

  it('calls router.back() when Back is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ExplorePage />)
    await user.click(screen.getByText('Back'))
    expect(routerBack).toHaveBeenCalledTimes(1)
  })

  it('shows an outcome badge when an outcome filter is present in the URL', async () => {
    searchParams = new URLSearchParams({ outcome: 'deny' })
    renderWithProviders(<ExplorePage />)
    expect(await screen.findByText('Deny')).toBeInTheDocument()
  })

  it('renders the summary stat bar once loaded', async () => {
    renderWithProviders(<ExplorePage />)
    expect(await screen.findByText('42')).toBeInTheDocument() // Total
    expect(screen.getByText('30')).toBeInTheDocument() // Allowed
    expect(screen.getByText('10')).toBeInTheDocument() // Denied
  })

  it('renders the by-agent and by-tool breakdown tables', async () => {
    renderWithProviders(<ExplorePage />)
    expect(await screen.findByText('billing-agent')).toBeInTheDocument()
    expect(screen.getByText('issue_refund')).toBeInTheDocument()
  })

  it('shows "No agent data" / "No tool data" when breakdowns are empty', async () => {
    ;(api.getExplore as jest.Mock).mockResolvedValue(explore({ agents: [], tools: [] }))
    renderWithProviders(<ExplorePage />)
    expect(await screen.findByText('No agent data')).toBeInTheDocument()
    expect(screen.getByText('No tool data')).toBeInTheDocument()
  })

  it('navigates with an agent_id filter when a breakdown row is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ExplorePage />)

    await user.click(await screen.findByText('billing-agent'))

    expect(routerPush).toHaveBeenCalledTimes(1)
    const url = routerPush.mock.calls[0][0] as string
    expect(new URLSearchParams(url.split('?')[1]).get('agent_id')).toBe('billing-agent')
  })

  it('shows a message when there are no records in the window', async () => {
    renderWithProviders(<ExplorePage />)
    expect(await screen.findByText('No records found for this window.')).toBeInTheDocument()
  })

  it('expands a record on click to show its parameters', async () => {
    const user = userEvent.setup()
    // A tool_name distinct from the by-tool breakdown table's default
    // ("issue_refund") so the two don't collide in text queries.
    ;(api.getAuditRecords as jest.Mock).mockResolvedValue([record({ tool_name: 'update_crm' })])
    renderWithProviders(<ExplorePage />)

    await user.click(await screen.findByText('update_crm'))
    expect(screen.getByText('Parameters')).toBeInTheDocument()
    expect(screen.getByText(/"amount_usd": 500/)).toBeInTheDocument()

    // Clicking again collapses it.
    await user.click(screen.getByText('update_crm'))
    expect(screen.queryByText('Parameters')).not.toBeInTheDocument()
  })

  it('renders the stubbed chart panels', async () => {
    renderWithProviders(<ExplorePage />)
    expect(await screen.findByTestId('throughput-chart-stub')).toBeInTheDocument()
    expect(screen.getByTestId('latency-chart-stub')).toBeInTheDocument()
  })
})
