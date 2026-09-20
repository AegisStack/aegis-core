/**
 * WebSocket client for real-time audit record streaming.
 *
 * Authenticates via ?token= query parameter (JWT access token).
 * On auth rejection (close codes 4001/4003), attempts a token refresh
 * then reconnects with the new token.
 */

import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './auth'

export type AuditRecordMessage = { type: 'audit_record'; data: unknown }
export type EscalationMessage  = { type: 'escalation'; data: unknown }
export type HeartbeatMessage   = { type: 'heartbeat' }
export type ConnectedMessage   = { type: 'connected'; customer_id: string; message: string }

export type WebSocketMessage =
  | AuditRecordMessage
  | EscalationMessage
  | HeartbeatMessage
  | ConnectedMessage

const AUTH_CLOSE_CODES = new Set([4001, 4003])

export class AegisWebSocket {
  private ws: WebSocket | null = null
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  private pingInterval: ReturnType<typeof setInterval> | null = null
  private reconnectAttempts = 0
  private readonly maxReconnectAttempts = 5
  private readonly reconnectDelay = 3000
  private intentionalClose = false

  constructor(
    private readonly customerId: string,
    private readonly onMessage: (message: WebSocketMessage) => void,
    private readonly onConnect?: () => void,
    private readonly onDisconnect?: () => void,
    private readonly baseUrl: string = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
  ) {}

  connect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }

    this.intentionalClose = false

    try {
      const token = getAccessToken()
      const params = new URLSearchParams({ customer_id: this.customerId })
      if (token) params.set('token', token)
      const url = `${this.baseUrl}/ws/live?${params.toString()}`
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        this.reconnectAttempts = 0
        this.onConnect?.()

        if (this.pingInterval) clearInterval(this.pingInterval)

        this.pingInterval = setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send('ping')
          } else {
            clearInterval(this.pingInterval!)
            this.pingInterval = null
          }
        }, 25000)
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          this.onMessage(message)
        } catch {
          // malformed message — ignore
        }
      }

      this.ws.onclose = (event) => {
        if (this.pingInterval) {
          clearInterval(this.pingInterval)
          this.pingInterval = null
        }

        this.onDisconnect?.()

        if (this.intentionalClose) return

        if (AUTH_CLOSE_CODES.has(event.code)) {
          // Auth failure — try to refresh token then reconnect
          this.handleAuthFailureReconnect()
        } else {
          this.attemptReconnect()
        }
      }

      this.ws.onerror = () => {
        // onerror always precedes onclose; let onclose drive reconnect logic
      }
    } catch {
      this.attemptReconnect()
    }
  }

  private async handleAuthFailureReconnect() {
    try {
      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        clearTokens()
        if (typeof window !== 'undefined') window.location.href = '/login'
        return
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (!response.ok) {
        clearTokens()
        if (typeof window !== 'undefined') window.location.href = '/login'
        return
      }

      const data = await response.json()
      // The backend rotates refresh tokens on every use (the old one is
      // revoked), so persist the new one rather than reusing the old value.
      setTokens(data.access_token, data.refresh_token ?? refreshToken)
      this.connect()
    } catch {
      clearTokens()
      if (typeof window !== 'undefined') window.location.href = '/login'
    }
  }

  private attemptReconnect() {
    if (this.intentionalClose) return
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return

    this.reconnectAttempts++
    this.reconnectTimeout = setTimeout(() => {
      if (!this.intentionalClose) this.connect()
    }, this.reconnectDelay)
  }

  disconnect() {
    this.intentionalClose = true

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }

    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}
