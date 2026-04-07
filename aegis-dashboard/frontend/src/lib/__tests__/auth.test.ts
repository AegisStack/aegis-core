/**
 * Tests for authentication utilities.
 */

import {
  setAuthTokens,
  getAccessToken,
  getUser,
  clearAuth,
  isAuthenticated,
} from '../auth'

describe('Auth utilities', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
  })

  describe('setAuthTokens', () => {
    it('stores tokens in localStorage', () => {
      const tokens = {
        access_token: 'test_token_123',
        token_type: 'bearer',
        user: {
          user_id: '123',
          email: 'test@example.com',
          full_name: 'Test User',
          customer_id: 'customer_1',
          role: 'admin',
          is_active: true,
          is_verified: true,
        },
      }

      setAuthTokens(tokens)

      expect(localStorage.getItem('aegis_token')).toBe('test_token_123')
      expect(localStorage.getItem('aegis_user')).toBeTruthy()
    })
  })

  describe('getAccessToken', () => {
    it('returns token from localStorage', () => {
      localStorage.setItem('aegis_token', 'my_token')
      expect(getAccessToken()).toBe('my_token')
    })

    it('returns null when no token exists', () => {
      expect(getAccessToken()).toBeNull()
    })
  })

  describe('getUser', () => {
    it('returns parsed user from localStorage', () => {
      const user = {
        user_id: '123',
        email: 'test@example.com',
        full_name: 'Test User',
        customer_id: 'customer_1',
        role: 'viewer',
        is_active: true,
        is_verified: false,
      }

      localStorage.setItem('aegis_user', JSON.stringify(user))

      const retrieved = getUser()
      expect(retrieved).toEqual(user)
    })

    it('returns null when no user exists', () => {
      expect(getUser()).toBeNull()
    })

    it('returns null for invalid JSON', () => {
      localStorage.setItem('aegis_user', 'invalid json')
      expect(getUser()).toBeNull()
    })
  })

  describe('clearAuth', () => {
    it('removes auth data from localStorage', () => {
      localStorage.setItem('aegis_token', 'token')
      localStorage.setItem('aegis_user', '{}')

      clearAuth()

      expect(localStorage.getItem('aegis_token')).toBeNull()
      expect(localStorage.getItem('aegis_user')).toBeNull()
    })
  })

  describe('isAuthenticated', () => {
    it('returns true when token exists', () => {
      localStorage.setItem('aegis_token', 'token')
      expect(isAuthenticated()).toBe(true)
    })

    it('returns false when no token exists', () => {
      expect(isAuthenticated()).toBe(false)
    })
  })
})
