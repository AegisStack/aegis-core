'use client'

import { useEffect, useState, useRef } from 'react'
import { AegisWebSocket, type WebSocketMessage } from '@/lib/websocket'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { formatRelativeTime } from '@/lib/utils'

interface LiveFeedProps {
  customerId: string
  maxItems?: number
}

export function LiveFeed({ customerId, maxItems = 10 }: LiveFeedProps) {
  const [messages, setMessages] = useState<any[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<AegisWebSocket | null>(null)

  useEffect(() => {
    // Only run in browser
    if (typeof window === 'undefined') return

    const ws = new AegisWebSocket(
      customerId,
      (message: WebSocketMessage) => {
        if (message.type === 'audit_record') {
          setMessages((prev) => [
            { ...message.data, timestamp: new Date().toISOString() },
            ...prev.slice(0, maxItems - 1),
          ])
        } else if (message.type === 'escalation') {
          setMessages((prev) => [
            { ...message.data, timestamp: new Date().toISOString(), isEscalation: true },
            ...prev.slice(0, maxItems - 1),
          ])
        }
      },
      () => setIsConnected(true),
      () => setIsConnected(false),
      process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
    )

    ws.connect()
    wsRef.current = ws

    return () => {
      ws.disconnect()
    }
  }, [customerId, maxItems])

  const getOutcomeBadge = (outcome: string) => {
    switch (outcome) {
      case 'allow':
        return <Badge variant="success">Allow</Badge>
      case 'deny':
        return <Badge variant="destructive">Deny</Badge>
      case 'escalate':
        return <Badge variant="warning">Escalate</Badge>
      default:
        return <Badge>{outcome}</Badge>
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Live Feed</CardTitle>
            <CardDescription>Real-time audit records</CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-muted-foreground">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {messages.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            Waiting for new events...
          </p>
        ) : (
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {messages.map((msg, index) => (
              <div
                key={index}
                className="p-3 border rounded-lg bg-accent/50 animate-in fade-in slide-in-from-top-2 duration-300"
              >
                <div className="flex items-start justify-between mb-1">
                  <div className="flex items-center space-x-2">
                    {msg.isEscalation ? (
                      <Badge variant="warning">Escalation</Badge>
                    ) : (
                      getOutcomeBadge(msg.outcome)
                    )}
                    <code className="text-sm font-mono">
                      {msg.tool_name || msg.escalation_id}
                    </code>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatRelativeTime(msg.timestamp)}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground truncate">
                  {msg.reason || msg.agent_id}
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
