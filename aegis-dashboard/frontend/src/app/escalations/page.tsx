'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Escalation } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatDate, formatRelativeTime } from '@/lib/utils'
import { useCustomer } from '@/app/providers'

function getTimeRemaining(expiresAt: string): string {
  const now = new Date()
  const expires = new Date(expiresAt)
  const diffMs = expires.getTime() - now.getTime()

  if (diffMs < 0) return 'Expired'

  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 60) return `${diffMins}m remaining`

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h remaining`

  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d remaining`
}

function EscalationCard({ escalation, onResolve }: {
  escalation: Escalation
  onResolve: (id: string, resolution: 'approved' | 'denied') => void
}) {
  const [isResolving, setIsResolving] = useState(false)
  const timeRemaining = getTimeRemaining(escalation.expires_at)
  const isExpired = timeRemaining === 'Expired'

  const handleResolve = async (resolution: 'approved' | 'denied') => {
    setIsResolving(true)
    try {
      await onResolve(escalation.escalation_id, resolution)
    } finally {
      setIsResolving(false)
    }
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg">
              <code className="font-mono">{escalation.tool_name}</code>
            </CardTitle>
            <CardDescription>{escalation.agent_id}</CardDescription>
          </div>
          <div className="text-right space-y-1">
            {isExpired ? (
              <Badge variant="destructive">Expired</Badge>
            ) : (
              <Badge variant="warning">{timeRemaining}</Badge>
            )}
            <p className="text-xs text-muted-foreground">
              {formatRelativeTime(escalation.created_at)}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <h4 className="text-sm font-semibold mb-2">Reason</h4>
          <p className="text-sm text-muted-foreground">{escalation.reason}</p>
        </div>

        <div>
          <h4 className="text-sm font-semibold mb-2">Parameters</h4>
          <pre className="bg-muted p-3 rounded-md text-xs overflow-x-auto">
            {JSON.stringify(escalation.params, null, 2)}
          </pre>
        </div>

        {escalation.status === 'pending' && !isExpired && (
          <div className="flex space-x-2 pt-2">
            <button
              className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={() => handleResolve('approved')}
              disabled={isResolving}
            >
              {isResolving ? 'Processing...' : 'Approve'}
            </button>
            <button
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={() => handleResolve('denied')}
              disabled={isResolving}
            >
              {isResolving ? 'Processing...' : 'Deny'}
            </button>
          </div>
        )}

        {escalation.status !== 'pending' && (
          <div className="pt-2 border-t">
            <p className="text-sm">
              <span className="text-muted-foreground">Resolution: </span>
              <Badge variant={escalation.status === 'approved' ? 'success' : 'destructive'}>
                {escalation.status}
              </Badge>
              {escalation.resolved_by && (
                <span className="text-muted-foreground ml-2">
                  by {escalation.resolved_by}
                </span>
              )}
            </p>
          </div>
        )}

        <div className="pt-2 border-t">
          <p className="text-xs text-muted-foreground">
            Escalation ID: {escalation.escalation_id}
          </p>
          <p className="text-xs text-muted-foreground">
            Audit Record: {escalation.record_id}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

export default function EscalationsPage() {
  const { customerId } = useCustomer()
  const [statusFilter, setStatusFilter] = useState<string>('pending')
  const queryClient = useQueryClient()

  const { data: escalations, isLoading } = useQuery({
    queryKey: ['escalations', customerId, statusFilter],
    queryFn: () =>
      api.getEscalations({
        customer_id: customerId,
        status: statusFilter,
      }),
    refetchInterval: statusFilter === 'pending' ? 5000 : false, // Refresh pending every 5s
  })

  const resolveMutation = useMutation({
    mutationFn: ({ id, resolution }: { id: string; resolution: 'approved' | 'denied' }) =>
      api.resolveEscalation(id, {
        resolution,
        resolved_by: `operator@${customerId}`,
      }),
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['escalations'] })
    },
  })

  const handleResolve = async (id: string, resolution: 'approved' | 'denied') => {
    await resolveMutation.mutateAsync({ id, resolution })
  }

  const pendingCount = escalations?.filter((e) => e.status === 'pending').length || 0

  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto px-4 py-8">
        {/* Status Filter */}
        <div className="mb-6 flex space-x-2">
          {['pending', 'approved', 'denied', 'expired'].map((status) => (
            <button
              key={status}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${
                statusFilter === status
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              }`}
              onClick={() => setStatusFilter(status)}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>

        {/* Escalation List */}
        {isLoading && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Loading escalations...</p>
          </div>
        )}

        {!isLoading && escalations && escalations.length === 0 && (
          <Card>
            <CardContent className="text-center py-12">
              <p className="text-muted-foreground">
                No {statusFilter} escalations found
              </p>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {escalations?.map((escalation) => (
            <EscalationCard
              key={escalation.escalation_id}
              escalation={escalation}
              onResolve={handleResolve}
            />
          ))}
        </div>

        {statusFilter === 'pending' && (
          <div className="mt-8 p-4 bg-muted rounded-lg">
            <h3 className="font-semibold mb-2">About Escalations</h3>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Escalations require human approval before tool execution</li>
              <li>• Pending escalations expire after the configured timeout period</li>
              <li>• Approving an escalation allows the tool call to proceed</li>
              <li>• Denying an escalation blocks the tool call</li>
              <li>• This page auto-refreshes every 5 seconds for pending escalations</li>
            </ul>
          </div>
        )}
      </main>
    </div>
  )
}
