/**
 * Tests for token storage helpers.
 */

import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../auth'

describe('token storage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns null for both tokens when nothing is stored', () => {
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })

  it('round-trips access and refresh tokens through setTokens', () => {
    setTokens('access-123', 'refresh-456')
    expect(getAccessToken()).toBe('access-123')
    expect(getRefreshToken()).toBe('refresh-456')
  })

  it('overwrites previously stored tokens', () => {
    setTokens('first-access', 'first-refresh')
    setTokens('second-access', 'second-refresh')
    expect(getAccessToken()).toBe('second-access')
    expect(getRefreshToken()).toBe('second-refresh')
  })

  it('clearTokens removes both tokens', () => {
    setTokens('access-123', 'refresh-456')
    clearTokens()
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })

  it('clearTokens is a no-op when nothing was stored', () => {
    expect(() => clearTokens()).not.toThrow()
    expect(getAccessToken()).toBeNull()
  })

  it('persists tokens under distinct storage keys from other app data', () => {
    setTokens('access-123', 'refresh-456')
    localStorage.setItem('aegis_customer_id', 'acme-corp')
    clearTokens()
    // Clearing tokens must not touch unrelated localStorage keys.
    expect(localStorage.getItem('aegis_customer_id')).toBe('acme-corp')
  })
})
