/**
 * Tests for the escalations page.
 */

import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test-utils'
import EscalationsPage from '../page'
import { api, type Escalation } from '@/lib/api'

jest.mock('@/lib/api', () => ({
  api: { getEscalations: jest.fn(), resolveEscalation: jest.fn() },
}))

function escalation(overrides: Partial<Escalation> = {}): Escalation {
  return {
    escalation_id: 'esc-1',
    record_id: 'rec-1',
    agent_id: 'billing-agent',
    tool_name: 'issue_refund',
    params: { amount_usd: 500 },
    reason: 'Amount exceeds limit',
    status: 'pending',
    created_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 20 * 60 * 1000).toISOString(),
    ...overrides,
  }
}

describe('EscalationsPage', () => {
  beforeEach(() => {
    ;(api.getEscalations as jest.Mock).mockReset()
    ;(api.resolveEscalation as jest.Mock).mockReset()
  })

  it('shows a loading message while escalations are being fetched', () => {
    ;(api.getEscalations as jest.Mock).mockReturnValue(new Promise(() => {}))
    renderWithProviders(<EscalationsPage />)
    expect(screen.getByText('Loading escalations...')).toBeInTheDocument()
  })

  it('shows an empty message for the current status filter', async () => {
    ;(api.getEscalations as jest.Mock).mockResolvedValue([])
    renderWithProviders(<EscalationsPage />)
    expect(await screen.findByText('No pending escalations found')).toBeInTheDocument()
  })

  it('defaults to the pending filter and requests it from the API', () => {
    ;(api.getEscalations as jest.Mock).mockResolvedValue([])
    renderWithProviders(<EscalationsPage />, { customerId: 'acme-corp' })
    expect(api.getEscalations).toHaveBeenCalledWith({
      customer_id: 'acme-corp',
      status: 'pending',
    })
  })

  it('switches status filter and refetches when a tab is clicked', async () => {
    const user = userEvent.setup()
    ;(api.getEscalations as jest.Mock).mockResolvedValue([])
    renderWithProviders(<EscalationsPage />)
    await screen.findByText('No pending escalations found')

    await user.click(screen.getByRole('button', { name: 'Approved' }))

    expect(api.getEscalations).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'approved' })
    )
    expect(await screen.findByText('No approved escalations found')).toBeInTheDocument()
  })

  it('renders a pending escalation with Approve/Deny actions', async () => {
    ;(api.getEscalations as jest.Mock).mockResolvedValue([escalation()])
    renderWithProviders(<EscalationsPage />)

    expect(await screen.findByText('issue_refund')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Deny' })).toBeInTheDocument()
  })

  it('resolves an escalation as approved when Approve is clicked', async () => {
    const user = userEvent.setup()
    ;(api.getEscalations as jest.Mock).mockResolvedValue([escalation({ escalation_id: 'esc-42' })])
    ;(api.resolveEscalation as jest.Mock).mockResolvedValue(escalation({ status: 'approved' }))

    renderWithProviders(<EscalationsPage />)
    await user.click(await screen.findByRole('button', { name: 'Approve' }))

    expect(api.resolveEscalation).toHaveBeenCalledWith('esc-42', { resolution: 'approved' })
  })

  it('shows the resolution and resolver for a non-pending escalation', async () => {
    ;(api.getEscalations as jest.Mock).mockResolvedValue([
      escalation({ status: 'denied', resolved_by: 'operator@acme.com' }),
    ])
    renderWithProviders(<EscalationsPage />)

    expect(await screen.findByText('denied')).toBeInTheDocument()
    expect(screen.getByText('by operator@acme.com')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
  })

  it('shows an Expired badge instead of actions once the deadline has passed', async () => {
    ;(api.getEscalations as jest.Mock).mockResolvedValue([
      escalation({ expires_at: new Date(Date.now() - 60 * 1000).toISOString() }),
    ])
    renderWithProviders(<EscalationsPage />)

    expect(await screen.findByText('Expired')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
  })
})
