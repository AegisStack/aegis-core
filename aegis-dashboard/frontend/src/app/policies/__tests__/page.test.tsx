/**
 * Tests for the policies page.
 *
 * Covers the two top-level tabs (agent overview, manage/version-history +
 * editor) and the create/rollback mutations. Does not exercise every
 * nested control (assign-to-agent form, YAML preview parsing) - those are
 * lower-risk, purely-local UI state on top of the same tested data flow.
 */

import { screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test-utils'
import PoliciesPage from '../page'
import { api, type Policy } from '@/lib/api'

jest.mock('@/lib/api', () => ({
  api: {
    getAgents: jest.fn(),
    getPolicies: jest.fn(),
    createPolicy: jest.fn(),
    activatePolicy: jest.fn(),
    assignPolicy: jest.fn(),
  },
}))

function policy(overrides: Partial<Policy> = {}): Policy {
  return {
    policy_id: 'pol-1',
    customer_id: 'acme-corp',
    agent_id: 'billing-agent',
    policy_yaml: 'version: 1\nrules: []',
    policy_hash: 'abc123def456',
    version: 1,
    is_active: true,
    created_at: new Date().toISOString(),
    ...overrides,
  }
}

describe('PoliciesPage', () => {
  beforeEach(() => {
    ;(api.getAgents as jest.Mock).mockReset().mockResolvedValue(['billing-agent'])
    ;(api.getPolicies as jest.Mock).mockReset().mockResolvedValue([])
    ;(api.createPolicy as jest.Mock).mockReset()
    ;(api.activatePolicy as jest.Mock).mockReset()
  })

  describe('Agent Overview tab (default)', () => {
    it('shows a message when there are no agents yet', async () => {
      ;(api.getAgents as jest.Mock).mockResolvedValue([])
      renderWithProviders(<PoliciesPage />)
      expect(
        await screen.findByText('No agents found. Create a policy to register an agent.')
      ).toBeInTheDocument()
    })

    it('renders a card per agent with its active policy version', async () => {
      ;(api.getAgents as jest.Mock).mockResolvedValue(['billing-agent'])
      ;(api.getPolicies as jest.Mock).mockResolvedValue([policy({ version: 3 })])
      renderWithProviders(<PoliciesPage />)

      expect(await screen.findByText('billing-agent')).toBeInTheDocument()
      expect(screen.getByText('Active v3')).toBeInTheDocument()
    })

    it('shows "No Policy" for an agent with no active policy', async () => {
      ;(api.getAgents as jest.Mock).mockResolvedValue(['ops-agent'])
      ;(api.getPolicies as jest.Mock).mockResolvedValue([])
      renderWithProviders(<PoliciesPage />)

      expect(await screen.findByText('No Policy')).toBeInTheDocument()
    })

    it('switches to the Manage tab for an agent via "Manage Policies"', async () => {
      const user = userEvent.setup()
      ;(api.getAgents as jest.Mock).mockResolvedValue(['billing-agent'])
      renderWithProviders(<PoliciesPage />)

      await user.click(await screen.findByText('Manage Policies'))

      expect(screen.getByText('Agent Selection')).toBeInTheDocument()
    })
  })

  describe('Manage Policies tab', () => {
    async function openManageTab(user: ReturnType<typeof userEvent.setup>) {
      renderWithProviders(<PoliciesPage />)
      await user.click(await screen.findByText('Manage Policies'))
    }

    it('shows a loading message while policies are being fetched', async () => {
      const user = userEvent.setup()
      ;(api.getPolicies as jest.Mock).mockReturnValue(new Promise(() => {}))
      await openManageTab(user)
      expect(await screen.findByText('Loading policies…')).toBeInTheDocument()
    })

    it('shows version history once loaded', async () => {
      const user = userEvent.setup()
      ;(api.getPolicies as jest.Mock).mockResolvedValue([
        policy({ policy_id: 'p1', version: 1, is_active: false }),
        policy({ policy_id: 'p2', version: 2, is_active: true }),
      ])
      await openManageTab(user)

      expect(await screen.findByText('Version 1')).toBeInTheDocument()
      expect(screen.getByText('Version 2')).toBeInTheDocument()
      expect(screen.getByText('Active')).toBeInTheDocument()
    })

    it('rolls back to a previous version via "Rollback"', async () => {
      const user = userEvent.setup()
      ;(api.getPolicies as jest.Mock).mockResolvedValue([
        policy({ policy_id: 'p1', version: 1, is_active: false }),
      ])
      ;(api.activatePolicy as jest.Mock).mockResolvedValue(policy({ policy_id: 'p1', is_active: true }))
      await openManageTab(user)

      await user.click(await screen.findByText('Rollback'))
      expect(api.activatePolicy).toHaveBeenCalledWith('p1')
    })

    it('creates a new policy version from the editor', async () => {
      const user = userEvent.setup()
      ;(api.createPolicy as jest.Mock).mockResolvedValue(policy())
      await openManageTab(user)

      await user.click(await screen.findByText('Create New Version'))
      expect(screen.getByText('Policy Editor')).toBeInTheDocument()

      await user.click(screen.getByText('Save Policy'))

      expect(api.createPolicy).toHaveBeenCalledWith(
        expect.objectContaining({
          agent_id: 'billing-agent',
          customer_id: 'test-customer',
        })
      )
    })

    it('shows a validation error and blocks saving when required fields are missing', async () => {
      const user = userEvent.setup()
      await openManageTab(user)
      await user.click(await screen.findByText('Create New Version'))

      const textarea = screen.getByPlaceholderText('Enter your policy YAML...')
      // userEvent.type() parses [ and { as special-key syntax, so a literal
      // "rules: []" is set directly via a change event instead.
      fireEvent.change(textarea, { target: { value: 'rules: []' } })

      expect(await screen.findByText('Missing required field: version')).toBeInTheDocument()
      expect(screen.getByText('Save Policy')).toBeDisabled()
      expect(api.createPolicy).not.toHaveBeenCalled()
    })
  })
})
