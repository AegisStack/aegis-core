/**
 * Tests for LiveFeed.
 *
 * @/lib/websocket is mocked wholesale: LiveFeed's own contract with
 * AegisWebSocket (constructor args, connect/disconnect lifecycle, and
 * reacting to the callbacks it's given) is what's under test here, not
 * AegisWebSocket's internals - those are covered by websocket.test.ts.
 */

import { render, screen, act } from '@testing-library/react'
import { LiveFeed } from '../LiveFeed'

type Callbacks = {
  onMessage: (message: unknown) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

let lastInstance: {
  customerId: string
  callbacks: Callbacks
  connect: jest.Mock
  disconnect: jest.Mock
} | null = null

jest.mock('@/lib/websocket', () => ({
  AegisWebSocket: jest.fn().mockImplementation((customerId, onMessage, onConnect, onDisconnect) => {
    const instance = {
      customerId,
      callbacks: { onMessage, onConnect, onDisconnect },
      connect: jest.fn(),
      disconnect: jest.fn(),
    }
    lastInstance = instance
    return instance
  }),
}))

describe('LiveFeed', () => {
  beforeEach(() => {
    lastInstance = null
  })

  it('shows a waiting message and Disconnected status before anything arrives', () => {
    render(<LiveFeed customerId="acme-corp" />)
    expect(screen.getByText('Waiting for new events...')).toBeInTheDocument()
    expect(screen.getByText('Disconnected')).toBeInTheDocument()
  })

  it('connects a websocket scoped to the given customerId on mount', () => {
    render(<LiveFeed customerId="acme-corp" />)
    expect(lastInstance?.customerId).toBe('acme-corp')
    expect(lastInstance?.connect).toHaveBeenCalledTimes(1)
  })

  it('disconnects the websocket on unmount', () => {
    const { unmount } = render(<LiveFeed customerId="acme-corp" />)
    const instance = lastInstance!
    unmount()
    expect(instance.disconnect).toHaveBeenCalledTimes(1)
  })

  it('shows Connected once onConnect fires', () => {
    render(<LiveFeed customerId="acme-corp" />)
    act(() => {
      lastInstance!.callbacks.onConnect?.()
    })
    expect(screen.getByText('Connected')).toBeInTheDocument()
  })

  it('renders an incoming audit_record message', () => {
    render(<LiveFeed customerId="acme-corp" />)
    act(() => {
      lastInstance!.callbacks.onMessage({
        type: 'audit_record',
        data: { tool_name: 'issue_refund', outcome: 'deny', reason: 'amount exceeds limit' },
      })
    })

    expect(screen.getByText('issue_refund')).toBeInTheDocument()
    expect(screen.getByText('Deny')).toBeInTheDocument()
    expect(screen.getByText('amount exceeds limit')).toBeInTheDocument()
  })

  it('renders an incoming escalation message with an Escalation badge', () => {
    render(<LiveFeed customerId="acme-corp" />)
    act(() => {
      lastInstance!.callbacks.onMessage({
        type: 'escalation',
        data: { escalation_id: 'esc_123', agent_id: 'billing-agent' },
      })
    })

    expect(screen.getByText('Escalation')).toBeInTheDocument()
    expect(screen.getByText('esc_123')).toBeInTheDocument()
  })

  it('ignores heartbeat/connected messages (no list item added)', () => {
    render(<LiveFeed customerId="acme-corp" />)
    act(() => {
      lastInstance!.callbacks.onMessage({ type: 'heartbeat' })
    })
    expect(screen.getByText('Waiting for new events...')).toBeInTheDocument()
  })

  it('caps the rendered list at maxItems', () => {
    render(<LiveFeed customerId="acme-corp" maxItems={2} />)
    act(() => {
      for (const tool of ['tool_a', 'tool_b', 'tool_c']) {
        lastInstance!.callbacks.onMessage({
          type: 'audit_record',
          data: { tool_name: tool, outcome: 'allow', reason: 'ok' },
        })
      }
    })

    expect(screen.queryByText('tool_a')).not.toBeInTheDocument()
    expect(screen.getByText('tool_b')).toBeInTheDocument()
    expect(screen.getByText('tool_c')).toBeInTheDocument()
  })
})
