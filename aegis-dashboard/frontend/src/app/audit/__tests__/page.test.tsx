/**
 * Tests for the audit log page.
 */

import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test-utils'
import AuditLogPage from '../page'
import { api, type AuditRecord } from '@/lib/api'

let searchParams = new URLSearchParams()

jest.mock('next/navigation', () => ({
  useSearchParams: () => searchParams,
}))

jest.mock('@/lib/api', () => ({
  api: { getAuditRecords: jest.fn() },
}))

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

describe('AuditLogPage', () => {
  beforeEach(() => {
    searchParams = new URLSearchParams()
    ;(api.getAuditRecords as jest.Mock).mockReset()
  })

  it('shows a loading message while records are being fetched', () => {
    ;(api.getAuditRecords as jest.Mock).mockReturnValue(new Promise(() => {}))
    renderWithProviders(<AuditLogPage />)
    expect(screen.getByText('Loading records...')).toBeInTheDocument()
  })

  it('shows an empty message when there are no records', async () => {
    ;(api.getAuditRecords as jest.Mock).mockResolvedValue([])
    renderWithProviders(<AuditLogPage />)
    expect(await screen.findByText('No records found')).toBeInTheDocument()
    expect(screen.getByText('0 records found')).toBeInTheDocument()
  })

  it('renders each record with its outcome badge and tool name', async () => {
    ;(api.getAuditRecords as jest.Mock).mockResolvedValue([
      record({ record_id: 'r1', tool_name: 'issue_refund', outcome: 'deny' }),
      record({ record_id: 'r2', tool_name: 'update_crm', outcome: 'allow' }),
    ])
    renderWithProviders(<AuditLogPage />)

    expect(await screen.findByText('issue_refund')).toBeInTheDocument()
    expect(screen.getByText('update_crm')).toBeInTheDocument()
    expect(screen.getByText('2 records found')).toBeInTheDocument()
  })

  it('opens a detail view when a record is clicked, and closes on ✕', async () => {
    const user = userEvent.setup()
    ;(api.getAuditRecords as jest.Mock).mockResolvedValue([
      record({ record_id: 'r1', tool_name: 'issue_refund', reason: 'Amount exceeds limit' }),
    ])
    renderWithProviders(<AuditLogPage />)

    await user.click(await screen.findByText('issue_refund'))

    expect(screen.getByText('Audit Record Detail')).toBeInTheDocument()
    expect(screen.getByText('r1')).toBeInTheDocument()

    await user.click(screen.getByText('✕'))
    expect(screen.queryByText('Audit Record Detail')).not.toBeInTheDocument()
  })

  it('applies the agent_id filter from the query string on mount', async () => {
    searchParams = new URLSearchParams({ agent_id: 'billing-agent' })
    ;(api.getAuditRecords as jest.Mock).mockResolvedValue([])
    renderWithProviders(<AuditLogPage />)

    await screen.findByText('0 records found')
    expect(api.getAuditRecords).toHaveBeenCalledWith(
      expect.objectContaining({ agent_id: 'billing-agent' })
    )
  })

  it('clears filters when "Clear Filters" is clicked', async () => {
    const user = userEvent.setup()
    ;(api.getAuditRecords as jest.Mock).mockResolvedValue([])
    renderWithProviders(<AuditLogPage />)
    await screen.findByText('0 records found')

    const agentInput = screen.getByPlaceholderText('e.g., billing-agent')
    await user.type(agentInput, 'billing-agent')
    expect(agentInput).toHaveValue('billing-agent')

    await user.click(screen.getByText('Clear Filters'))
    expect(agentInput).toHaveValue('')
  })

  it('shows execution error details in the record modal when present', async () => {
    const user = userEvent.setup()
    ;(api.getAuditRecords as jest.Mock).mockResolvedValue([
      record({ tool_name: 'deploy', execution_error: 'permission denied' }),
    ])
    renderWithProviders(<AuditLogPage />)

    await user.click(await screen.findByText('deploy'))
    expect(screen.getByText('permission denied')).toBeInTheDocument()
  })
})
