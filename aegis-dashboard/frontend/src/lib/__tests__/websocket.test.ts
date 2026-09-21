/**
 * Tests for AegisWebSocket: connection URL, message dispatch, and the
 * reconnect-on-4001/4003 (auth failure) behavior.
 */

import { AegisWebSocket } from '../websocket'
import { setTokens, getRefreshToken } from '../auth'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1
  static CLOSED = 3

  url: string
  readyState = MockWebSocket.OPEN
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: ((event: { code: number }) => void) | null = null
  onerror: (() => void) | null = null
  sent: string[] = []
  closed = false

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.closed = true
    this.readyState = MockWebSocket.CLOSED
  }

  // Test helpers to drive the socket from outside.
  triggerOpen() {
    this.onopen?.()
  }
  triggerMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }
  triggerClose(code: number) {
    this.onclose?.({ code })
  }
}

describe('AegisWebSocket', () => {
  const baseUrl = 'ws://test-host:8000'

  beforeEach(() => {
    jest.useFakeTimers()
    localStorage.clear()
    MockWebSocket.instances = []
    // @ts-expect-error - test double for the browser global
    global.WebSocket = MockWebSocket
    global.fetch = jest.fn()
  })

  afterEach(() => {
    jest.useRealTimers()
    jest.restoreAllMocks()
  })

  function latestSocket(): MockWebSocket {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1]
  }

  // window.location's setter type is `string` (assigning it navigates), so
  // swapping in a test double needs defineProperty rather than a direct
  // assignment to stay type-correct.
  function stubLocation() {
    const original = window.location
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...original, href: '' },
    })
    return () => {
      Object.defineProperty(window, 'location', { configurable: true, value: original })
    }
  }

  it('connects to /ws/live with customer_id and the stored access token', () => {
    setTokens('my-access-token', 'my-refresh-token')
    const ws = new AegisWebSocket('acme-corp', jest.fn(), undefined, undefined, baseUrl)
    ws.connect()

    const url = new URL(latestSocket().url)
    expect(url.origin + url.pathname).toBe(`${baseUrl}/ws/live`)
    expect(url.searchParams.get('customer_id')).toBe('acme-corp')
    expect(url.searchParams.get('token')).toBe('my-access-token')
  })

  it('omits the token param when no access token is stored', () => {
    const ws = new AegisWebSocket('acme-corp', jest.fn(), undefined, undefined, baseUrl)
    ws.connect()

    const url = new URL(latestSocket().url)
    expect(url.searchParams.has('token')).toBe(false)
  })

  it('calls onConnect and onMessage for incoming messages', () => {
    const onMessage = jest.fn()
    const onConnect = jest.fn()
    const ws = new AegisWebSocket('acme-corp', onMessage, onConnect, undefined, baseUrl)
    ws.connect()

    latestSocket().triggerOpen()
    expect(onConnect).toHaveBeenCalledTimes(1)

    latestSocket().triggerMessage({ type: 'heartbeat' })
    expect(onMessage).toHaveBeenCalledWith({ type: 'heartbeat' })
  })

  it('ignores malformed message payloads instead of throwing', () => {
    const onMessage = jest.fn()
    const ws = new AegisWebSocket('acme-corp', onMessage, undefined, undefined, baseUrl)
    ws.connect()
    latestSocket().triggerOpen()

    expect(() => latestSocket().onmessage?.({ data: 'not json' })).not.toThrow()
    expect(onMessage).not.toHaveBeenCalled()
  })

  it('calls onDisconnect when the socket closes', () => {
    const onDisconnect = jest.fn()
    const ws = new AegisWebSocket('acme-corp', jest.fn(), undefined, onDisconnect, baseUrl)
    ws.connect()
    latestSocket().triggerOpen()
    latestSocket().triggerClose(1000)

    expect(onDisconnect).toHaveBeenCalledTimes(1)
  })

  it('does not reconnect after an intentional disconnect()', () => {
    const ws = new AegisWebSocket('acme-corp', jest.fn(), undefined, undefined, baseUrl)
    ws.connect()
    const firstSocket = latestSocket()

    ws.disconnect()
    expect(firstSocket.closed).toBe(true)

    // A close event firing after disconnect() (e.g. the server ack) must
    // not trigger a reconnect attempt.
    firstSocket.triggerClose(1000)
    jest.advanceTimersByTime(10_000)
    expect(MockWebSocket.instances).toHaveLength(1)
  })

  it('schedules a plain reconnect on a non-auth close code', () => {
    const ws = new AegisWebSocket('acme-corp', jest.fn(), undefined, undefined, baseUrl)
    ws.connect()
    latestSocket().triggerClose(1006)

    expect(MockWebSocket.instances).toHaveLength(1)
    jest.advanceTimersByTime(3000)
    expect(MockWebSocket.instances).toHaveLength(2)
  })

  describe('auth failure reconnect (4001/4003)', () => {
    it('refreshes the token and reconnects on a 4001/4003 close', async () => {
      setTokens('old-access-token', 'old-refresh-token')
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access_token: 'new-access-token', refresh_token: 'new-refresh-token' }),
      })

      const ws = new AegisWebSocket('acme-corp', jest.fn(), undefined, undefined, baseUrl)
      ws.connect()
      latestSocket().triggerClose(4001)

      // handleAuthFailureReconnect is async - flush its microtasks.
      await Promise.resolve()
      await Promise.resolve()

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/auth/refresh'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ refresh_token: 'old-refresh-token' }),
        })
      )
      expect(getRefreshToken()).toBe('new-refresh-token')
      expect(MockWebSocket.instances).toHaveLength(2)
      expect(new URL(latestSocket().url).searchParams.get('token')).toBe('new-access-token')
    })

    it('clears tokens and redirects to /login when there is no refresh token', async () => {
      const restoreLocation = stubLocation()

      const ws = new AegisWebSocket('acme-corp', jest.fn(), undefined, undefined, baseUrl)
      ws.connect()
      latestSocket().triggerClose(4003)
      await Promise.resolve()

      expect(global.fetch).not.toHaveBeenCalled()
      expect(window.location.href).toBe('/login')

      restoreLocation()
    })

    it('clears tokens and redirects to /login when the refresh request fails', async () => {
      setTokens('old-access-token', 'old-refresh-token')
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({ ok: false })
      const restoreLocation = stubLocation()

      const ws = new AegisWebSocket('acme-corp', jest.fn(), undefined, undefined, baseUrl)
      ws.connect()
      latestSocket().triggerClose(4001)
      await Promise.resolve()
      await Promise.resolve()

      expect(localStorage.getItem('aegis_access_token')).toBeNull()
      expect(window.location.href).toBe('/login')

      restoreLocation()
    })
  })
})
