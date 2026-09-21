/**
 * Tests for the login page.
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginPage from '../page'
import { api } from '@/lib/api'
import { getAccessToken, getRefreshToken } from '@/lib/auth'

const push = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}))

jest.mock('@/lib/api', () => ({
  api: { login: jest.fn() },
}))

describe('LoginPage', () => {
  beforeEach(() => {
    push.mockClear()
    ;(api.login as jest.Mock).mockReset()
    localStorage.clear()
  })

  it('renders email and password fields and a submit button', () => {
    render(<LoginPage />)
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('logs in, stores tokens, and redirects home on success', async () => {
    const user = userEvent.setup()
    ;(api.login as jest.Mock).mockResolvedValueOnce({
      access_token: 'access-123',
      refresh_token: 'refresh-456',
      token_type: 'bearer',
      user: {},
    })

    render(<LoginPage />)
    await user.type(screen.getByLabelText('Email'), 'viewer@test.com')
    await user.type(screen.getByLabelText('Password'), 'viewer123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(api.login).toHaveBeenCalledWith({ email: 'viewer@test.com', password: 'viewer123' })
    expect(getAccessToken()).toBe('access-123')
    expect(getRefreshToken()).toBe('refresh-456')
    expect(push).toHaveBeenCalledWith('/')
  })

  it('shows the backend error message and does not redirect on failure', async () => {
    const user = userEvent.setup()
    ;(api.login as jest.Mock).mockRejectedValueOnce({
      response: { data: { detail: 'Incorrect email or password' } },
    })

    render(<LoginPage />)
    await user.type(screen.getByLabelText('Email'), 'viewer@test.com')
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Incorrect email or password')).toBeInTheDocument()
    expect(push).not.toHaveBeenCalled()
    expect(getAccessToken()).toBeNull()
  })

  it('falls back to a generic error message when the backend gives no detail', async () => {
    const user = userEvent.setup()
    ;(api.login as jest.Mock).mockRejectedValueOnce(new Error('network down'))

    render(<LoginPage />)
    await user.type(screen.getByLabelText('Email'), 'viewer@test.com')
    await user.type(screen.getByLabelText('Password'), 'viewer123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Invalid email or password')).toBeInTheDocument()
  })

  it('disables the submit button and shows progress text while submitting', async () => {
    const user = userEvent.setup()
    let resolveLogin: (value: unknown) => void
    ;(api.login as jest.Mock).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveLogin = resolve
      })
    )

    render(<LoginPage />)
    await user.type(screen.getByLabelText('Email'), 'viewer@test.com')
    await user.type(screen.getByLabelText('Password'), 'viewer123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(screen.getByRole('button', { name: 'Signing in…' })).toBeDisabled()

    resolveLogin!({ access_token: 'a', refresh_token: 'r', token_type: 'bearer', user: {} })
  })
})
