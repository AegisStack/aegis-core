'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type AuditRecord } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatDate, formatRelativeTime } from '@/lib/utils'

const DEMO_CUSTOMER_ID = 'acme-corp'

export default function AuditLogPage() {
  const [filters, setFilters] = useState({
    agent_id: '',
    tool_name: '',
    outcome: '',
  })
  const [selectedRecord, setSelectedRecord] = useState<AuditRecord | null>(null)

  const { data: records, isLoading } = useQuery({
    queryKey: ['audit-records', DEMO_CUSTOMER_ID, filters],
    queryFn: () =>
      api.getAuditRecords({
        customer_id: DEMO_CUSTOMER_ID,
        agent_id: filters.agent_id || undefined,
        tool_name: filters.tool_name || undefined,
        outcome: filters.outcome || undefined,
        limit: 100,
      }),
  })

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
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold">Audit Log Explorer</h1>
          <p className="text-sm text-muted-foreground">
            Query and analyze policy enforcement events
          </p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Filters */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle>Filters</CardTitle>
              <CardDescription>Refine your search</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Agent ID</label>
                <input
                  type="text"
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                  placeholder="e.g., billing-agent"
                  value={filters.agent_id}
                  onChange={(e) => setFilters({ ...filters, agent_id: e.target.value })}
                />
              </div>

              <div>
                <label className="text-sm font-medium">Tool Name</label>
                <input
                  type="text"
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                  placeholder="e.g., issue_refund"
                  value={filters.tool_name}
                  onChange={(e) => setFilters({ ...filters, tool_name: e.target.value })}
                />
              </div>

              <div>
                <label className="text-sm font-medium">Outcome</label>
                <select
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                  value={filters.outcome}
                  onChange={(e) => setFilters({ ...filters, outcome: e.target.value })}
                >
                  <option value="">All</option>
                  <option value="allow">Allow</option>
                  <option value="deny">Deny</option>
                  <option value="escalate">Escalate</option>
                </select>
              </div>

              <button
                className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                onClick={() => setFilters({ agent_id: '', tool_name: '', outcome: '' })}
              >
                Clear Filters
              </button>

              <div className="pt-4 border-t">
                <p className="text-sm text-muted-foreground">
                  {records?.length || 0} records found
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Audit Records</CardTitle>
              <CardDescription>Most recent first</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading && (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">Loading records...</p>
                </div>
              )}

              {!isLoading && records && records.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">No records found</p>
                </div>
              )}

              <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {records?.map((record) => (
                  <div
                    key={record.record_id}
                    className="p-4 border rounded-lg hover:bg-accent cursor-pointer transition-colors"
                    onClick={() => setSelectedRecord(record)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        {getOutcomeBadge(record.outcome)}
                        <code className="text-sm font-mono">{record.tool_name}</code>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {formatRelativeTime(record.timestamp)}
                      </span>
                    </div>

                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">{record.reason}</p>
                      <div className="flex items-center space-x-4 text-xs text-muted-foreground">
                        <span>Agent: {record.agent_id}</span>
                        <span>Rule: {record.matched_rule}</span>
                        {record.latency_ms && <span>Latency: {record.latency_ms.toFixed(2)}ms</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Detail Modal */}
        {selectedRecord && (
          <div
            className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
            onClick={() => setSelectedRecord(null)}
          >
            <Card
              className="max-w-2xl w-full max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Audit Record Detail</CardTitle>
                  <button
                    className="text-muted-foreground hover:text-foreground"
                    onClick={() => setSelectedRecord(null)}
                  >
                    ✕
                  </button>
                </div>
                <CardDescription>{selectedRecord.record_id}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h3 className="font-semibold mb-2">Overview</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">Timestamp:</span>
                      <p>{formatDate(selectedRecord.timestamp)}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Outcome:</span>
                      <p>{getOutcomeBadge(selectedRecord.outcome)}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Agent:</span>
                      <p>{selectedRecord.agent_id}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Tool:</span>
                      <p>{selectedRecord.tool_name}</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold mb-2">Parameters</h3>
                  <pre className="bg-muted p-3 rounded-md text-xs overflow-x-auto">
                    {JSON.stringify(selectedRecord.params, null, 2)}
                  </pre>
                </div>

                <div>
                  <h3 className="font-semibold mb-2">Policy Decision</h3>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">Matched Rule:</span>
                      <p className="font-mono text-xs">{selectedRecord.matched_rule}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Reason:</span>
                      <p>{selectedRecord.reason}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Policy Version:</span>
                      <p className="font-mono text-xs">{selectedRecord.policy_version}</p>
                    </div>
                  </div>
                </div>

                {selectedRecord.execution_result && (
                  <div>
                    <h3 className="font-semibold mb-2">Execution Result</h3>
                    <pre className="bg-muted p-3 rounded-md text-xs overflow-x-auto">
                      {JSON.stringify(selectedRecord.execution_result, null, 2)}
                    </pre>
                  </div>
                )}

                {selectedRecord.execution_error && (
                  <div>
                    <h3 className="font-semibold mb-2">Execution Error</h3>
                    <pre className="bg-destructive/10 text-destructive p-3 rounded-md text-xs overflow-x-auto">
                      {selectedRecord.execution_error}
                    </pre>
                  </div>
                )}

                {selectedRecord.escalation_id && (
                  <div>
                    <h3 className="font-semibold mb-2">Escalation</h3>
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">Escalation ID:</span>
                        <p className="font-mono text-xs">{selectedRecord.escalation_id}</p>
                      </div>
                      {selectedRecord.resolved_by && (
                        <>
                          <div>
                            <span className="text-muted-foreground">Resolved By:</span>
                            <p>{selectedRecord.resolved_by}</p>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Resolution:</span>
                            <p>{selectedRecord.resolution}</p>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  )
}
