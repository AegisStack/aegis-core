/**
 * Tests for the api client: auth interceptor behavior and endpoint calls.
 *
 * axios is mocked at the module level so these tests exercise the real
 * interceptor functions registered by api.ts (captured via the mocked
 * `interceptors.request.use`/`response.use` calls) without making network
 * requests.
 */

import { setTokens } from '../auth'

jest.mock('axios')

type Interceptor<T> = (arg: T) => any

describe('api client', () => {
  let requestFulfilled: Interceptor<any>
  let responseRejected: Interceptor<any>
  let mockClient: {
    get: jest.Mock
    post: jest.Mock
    interceptors: {
      request: { use: jest.Mock }
      response: { use: jest.Mock }
    }
  }
  let api: typeof import('../api').api

  beforeEach(() => {
    jest.resetModules()
    localStorage.clear()

    mockClient = {
      get: jest.fn().mockResolvedValue({ data: 'get-result' }),
      post: jest.fn().mockResolvedValue({ data: 'post-result' }),
      interceptors: {
        request: {
          use: jest.fn((onFulfilled: Interceptor<any>) => {
            requestFulfilled = onFulfilled
          }),
        },
        response: {
          use: jest.fn((_onFulfilled: Interceptor<any>, onRejected: Interceptor<any>) => {
            responseRejected = onRejected
          }),
        },
      },
    }

    // jest.resetModules() gives axios a fresh module instance too, so the
    // mock must be (re-)installed on that same fresh instance - grabbing
    // a reference from a `beforeEach`-scoped require, not an import at the
    // top of this file, is what keeps them in sync.
    const axios = require('axios')
    axios.create = jest.fn(() => mockClient)

    // Re-require so the module-level apiClient is built against the fresh mock.
    api = require('../api').api
  })

  describe('request interceptor', () => {
    it('attaches an Authorization header when an access token is stored', () => {
      setTokens('my-access-token', 'my-refresh-token')
      const config = requestFulfilled({ headers: {} })
      expect(config.headers.Authorization).toBe('Bearer my-access-token')
    })

    it('does not attach an Authorization header when no token is stored', () => {
      const config = requestFulfilled({ headers: {} })
      expect(config.headers.Authorization).toBeUndefined()
    })
  })

  describe('response interceptor', () => {
    const originalLocation = window.location

    beforeEach(() => {
      // jsdom throws "Not implemented: navigation" on a real href
      // assignment - replace location with a writable stand-in.
      // window.location's setter type is `string` (assigning navigates),
      // so defineProperty (not a direct assignment) is the type-correct
      // way to swap the whole object out for a test double.
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: { ...originalLocation, href: '', pathname: '/' },
      })
    })

    afterEach(() => {
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: originalLocation,
      })
    })

    it('clears tokens and redirects to /login on a 401', async () => {
      setTokens('my-access-token', 'my-refresh-token')
      const error = { response: { status: 401 } }

      await expect(responseRejected(error)).rejects.toBe(error)

      expect(localStorage.getItem('aegis_access_token')).toBeNull()
      expect(window.location.href).toBe('/login')
    })

    it('does not redirect again if already on /login', async () => {
      window.location.pathname = '/login'
      const error = { response: { status: 401 } }

      await expect(responseRejected(error)).rejects.toBe(error)

      expect(window.location.href).toBe('')
    })

    it('passes through non-401 errors without clearing tokens', async () => {
      setTokens('my-access-token', 'my-refresh-token')
      const error = { response: { status: 500 } }

      await expect(responseRejected(error)).rejects.toBe(error)

      expect(localStorage.getItem('aegis_access_token')).toBe('my-access-token')
      expect(window.location.href).toBe('')
    })
  })

  describe('endpoint calls', () => {
    it('login posts to /api/v1/auth/login with the given credentials', async () => {
      mockClient.post.mockResolvedValueOnce({
        data: { access_token: 'a', refresh_token: 'r', token_type: 'bearer', user: {} },
      })
      await api.login({ email: 'a@b.com', password: 'secret' })
      expect(mockClient.post).toHaveBeenCalledWith('/api/v1/auth/login', {
        email: 'a@b.com',
        password: 'secret',
      })
    })

    it('logout sends the refresh token when provided', async () => {
      await api.logout('my-refresh-token')
      expect(mockClient.post).toHaveBeenCalledWith('/api/v1/auth/logout', {
        refresh_token: 'my-refresh-token',
      })
    })

    it('logout sends an empty body when no refresh token is provided', async () => {
      await api.logout()
      expect(mockClient.post).toHaveBeenCalledWith('/api/v1/auth/logout', {})
    })

    it('getAuditRecords calls GET /api/v1/audit with query params', async () => {
      await api.getAuditRecords({ customer_id: 'acme-corp', limit: 50 })
      expect(mockClient.get).toHaveBeenCalledWith('/api/v1/audit', {
        params: { customer_id: 'acme-corp', limit: 50 },
      })
    })

    it('resolveEscalation posts resolution without a resolved_by field', async () => {
      await api.resolveEscalation('esc_1', { resolution: 'approved' })
      expect(mockClient.post).toHaveBeenCalledWith('/api/v1/escalations/esc_1/resolve', {
        resolution: 'approved',
      })
    })

    it('createPolicy posts to /api/v1/policies', async () => {
      await api.createPolicy({
        customer_id: 'acme-corp',
        agent_id: 'billing-agent',
        policy_yaml: 'version: 1\nrules: []',
      })
      expect(mockClient.post).toHaveBeenCalledWith('/api/v1/policies', {
        customer_id: 'acme-corp',
        agent_id: 'billing-agent',
        policy_yaml: 'version: 1\nrules: []',
      })
    })
  })
})
