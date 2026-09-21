/**
 * Tests for NavBar.
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NavBar } from '../NavBar'
import { CustomerContext } from '@/app/providers'
import { api } from '@/lib/api'
import { setTokens, getAccessToken } from '@/lib/auth'

const push = jest.fn()
let mockPathname = '/'

jest.mock('next/navigation', () => ({
  usePathname: () => mockPathname,
  useRouter: () => ({ push }),
}))

jest.mock('@/lib/api', () => ({
  api: { logout: jest.fn().mockResolvedValue(undefined) },
}))

function renderNavBar(customerId = 'acme-corp') {
  return render(
    <CustomerContext.Provider value={{ customerId, setCustomerId: jest.fn() }}>
      <NavBar />
    </CustomerContext.Provider>
  )
}

describe('NavBar', () => {
  beforeEach(() => {
    push.mockClear()
    ;(api.logout as jest.Mock).mockClear()
    localStorage.clear()
    mockPathname = '/'
  })

  it('renders all nav links', () => {
    renderNavBar()
    for (const label of ['Overview', 'Audit Log', 'Log Explorer', 'Escalations', 'Policies']) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
  })

  it('renders nothing on the /login route', () => {
    mockPathname = '/login'
    const { container } = renderNavBar()
    expect(container).toBeEmptyDOMElement()
  })

  it('shows the current customer in the switcher', () => {
    renderNavBar('beta-corp')
    expect(screen.getByRole('combobox')).toHaveValue('beta-corp')
  })

  it('logs out: calls api.logout with the refresh token, clears tokens, and redirects', async () => {
    const user = userEvent.setup()
    setTokens('access-1', 'refresh-1')
    renderNavBar()

    await user.click(screen.getByText('Log out'))

    expect(api.logout).toHaveBeenCalledWith('refresh-1')
    expect(getAccessToken()).toBeNull()
    expect(push).toHaveBeenCalledWith('/login')
  })

  it('still clears tokens and redirects if the logout request fails', async () => {
    const user = userEvent.setup()
    ;(api.logout as jest.Mock).mockRejectedValueOnce(new Error('network error'))
    setTokens('access-1', 'refresh-1')
    renderNavBar()

    await user.click(screen.getByText('Log out'))

    expect(getAccessToken()).toBeNull()
    expect(push).toHaveBeenCalledWith('/login')
  })

  it('persists the collapsed state to localStorage when toggled', async () => {
    const user = userEvent.setup()
    renderNavBar()

    await user.click(screen.getByTitle('Collapse sidebar'))

    expect(localStorage.getItem('aegis_sidebar_collapsed')).toBe('true')
  })
})
