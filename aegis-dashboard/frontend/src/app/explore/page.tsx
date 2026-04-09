'use client'

import { useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { api, type AuditRecord } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatDate, formatRelativeTime } from '@/lib/utils'
import { useCustomer } from '@/app/providers'
import { TimeRangePicker, type TimeRange } from '@/components/TimeRangePicker'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { ArrowLeft, Clock, ShieldCheck, ShieldX, AlertTriangle, Timer } from 'lucide-react'

function buildDefaultRange(): { start: string; end: string } {
  const end = new Date()
  const start = new Date(end.getTime() - 60 * 60 * 1000)
  return { start: start.toISOString(), end: end.toISOString() }
}

function formatWindowTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

function OutcomeBadge({ outcome }: { outcome: string }) {
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

function DenyRateBar({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100)
  const color = pct > 50 ? '#ef4444' : pct > 20 ? '#f59e0b' : '#22c55e'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs w-8 text-right" style={{ color }}>{pct}%</span>
    </div>
  )
}

function ExplorePageInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { customerId } = useCustomer()

  const defaults = buildDefaultRange()
  const outcome = searchParams.get('outcome') || ''
  const agentId = searchParams.get('agent_id') || ''

  const [timeRange, setTimeRange] = useState<TimeRange>(() => ({
    start: searchParams.get('start') || defaults.start,
    end: searchParams.get('end') || defaults.end,
    interval: '1m',
    label: searchParams.get('start') ? 'custom' : '1h',
  }))

  const [expandedRecordId, setExpandedRecordId] = useState<string | null>(null)

  const start = timeRange.start
  const end = timeRange.end

  const { data: explore, isLoading: exploreLoading } = useQuery({
    queryKey: ['explore', customerId, start, end, outcome, agentId],
    queryFn: () =>
      api.getExplore({
        customer_id: customerId,
        start,
        end,
        outcome: outcome || undefined,
        agent_id: agentId || undefined,
      }),
    enabled: !!(customerId && start && end),
  })

  const { data: records, isLoading: recordsLoading } = useQuery({
    queryKey: ['explore-records', customerId, start, end, outcome, agentId],
    queryFn: () =>
      api.getAuditRecords({
        customer_id: customerId,
        start_time: start,
        end_time: end,
        outcome: outcome || undefined,
        agent_id: agentId || undefined,
        limit: 200,
      }),
    enabled: !!(customerId && start && end),
  })

  const summary = explore?.summary
  const outcomeChartData = summary
    ? [
        { name: 'Allowed', value: summary.allows, color: '#22c55e' },
        { name: 'Denied', value: summary.denies, color: '#ef4444' },
        { name: 'Escalated', value: summary.escalations, color: '#f59e0b' },
      ].filter((d) => d.value > 0)
    : []

  const latencyChartData = summary
    ? [
        { name: 'Avg', value: summary.avg_latency, color: '#3b82f6' },
        { name: 'P95', value: summary.p95_latency, color: '#f59e0b' },
        { name: 'P99', value: summary.p99_latency, color: '#ef4444' },
      ]
    : []

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card px-6 py-4">
        <div className="flex items-center gap-4 mb-3">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <div className="flex-1 min-w-0">
            <div className="flex items-center flex-wrap gap-2">
              <h1 className="text-lg font-semibold">Log Explorer</h1>
              <div className="flex items-center gap-1.5 text-sm text-muted-foreground bg-muted px-2.5 py-1 rounded-md">
                <Clock className="h-3.5 w-3.5" />
                <span>{formatWindowTime(start)}</span>
                <span>→</span>
                <span>{formatWindowTime(end)}</span>
              </div>
              {outcome && (
                <OutcomeBadge outcome={outcome} />
              )}
              {agentId && (
                <span className="text-xs bg-muted px-2 py-0.5 rounded font-mono">{agentId}</span>
              )}
            </div>
          </div>
        </div>

        {/* Time range picker */}
        <div className="mb-3">
          <TimeRangePicker value={timeRange} onChange={setTimeRange} />
        </div>

        {/* Summary stat bar */}
        {exploreLoading ? (
          <div className="text-sm text-muted-foreground">Loading summary...</div>
        ) : summary ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
            <div className="bg-muted/50 rounded-lg px-3 py-2 text-center">
              <p className="text-xs text-muted-foreground">Total</p>
              <p className="text-xl font-bold">{summary.total.toLocaleString()}</p>
            </div>
            <div className="bg-green-500/10 rounded-lg px-3 py-2 text-center flex items-center justify-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-green-500 shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Allowed</p>
                <p className="text-xl font-bold text-green-600">{summary.allows.toLocaleString()}</p>
              </div>
            </div>
            <div className="bg-red-500/10 rounded-lg px-3 py-2 text-center flex items-center justify-center gap-1.5">
              <ShieldX className="h-4 w-4 text-red-500 shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Denied</p>
                <p className="text-xl font-bold text-red-600">{summary.denies.toLocaleString()}</p>
              </div>
            </div>
            <div className="bg-amber-500/10 rounded-lg px-3 py-2 text-center flex items-center justify-center gap-1.5">
              <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Escalated</p>
                <p className="text-xl font-bold text-amber-600">{summary.escalations.toLocaleString()}</p>
              </div>
            </div>
            <div className="bg-blue-500/10 rounded-lg px-3 py-2 text-center flex items-center justify-center gap-1.5">
              <Timer className="h-4 w-4 text-blue-500 shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Avg Latency</p>
                <p className="text-xl font-bold text-blue-600">{summary.avg_latency.toFixed(1)}ms</p>
              </div>
            </div>
            <div className="bg-muted/50 rounded-lg px-3 py-2 text-center">
              <p className="text-xs text-muted-foreground">P95</p>
              <p className="text-xl font-bold">{summary.p95_latency.toFixed(1)}ms</p>
            </div>
            <div className="bg-muted/50 rounded-lg px-3 py-2 text-center">
              <p className="text-xs text-muted-foreground">P99</p>
              <p className="text-xl font-bold">{summary.p99_latency.toFixed(1)}ms</p>
            </div>
          </div>
        ) : null}
      </div>

      <div className="px-6 py-6 space-y-6">
        {/* Mini charts row */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Outcome Distribution</CardTitle>
                <CardDescription className="text-xs">For this time window</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={outcomeChartData} layout="vertical">
                    <XAxis type="number" tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={60} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null
                        return (
                          <div className="bg-card border rounded-lg p-2 shadow-lg text-sm">
                            <p>{payload[0].payload.name}: <strong>{payload[0].value}</strong></p>
                          </div>
                        )
                      }}
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {outcomeChartData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Latency Breakdown</CardTitle>
                <CardDescription className="text-xs">Avg / P95 / P99 for this window</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={latencyChartData} layout="vertical">
                    <XAxis type="number" unit="ms" tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={35} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null
                        return (
                          <div className="bg-card border rounded-lg p-2 shadow-lg text-sm">
                            <p>{payload[0].payload.name}: <strong>{Number(payload[0].value).toFixed(2)}ms</strong></p>
                          </div>
                        )
                      }}
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {latencyChartData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Breakdown tables */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Per-agent table */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">By Agent</CardTitle>
              <CardDescription className="text-xs">Activity breakdown per agent in this window</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {exploreLoading ? (
                <p className="text-sm text-muted-foreground p-4">Loading...</p>
              ) : !explore?.agents?.length ? (
                <p className="text-sm text-muted-foreground p-4">No agent data</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40">
                        <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Agent</th>
                        <th className="text-right px-3 py-2 text-xs font-medium text-muted-foreground">Calls</th>
                        <th className="text-right px-3 py-2 text-xs font-medium text-muted-foreground">Denied</th>
                        <th className="px-3 py-2 text-xs font-medium text-muted-foreground w-32">Deny Rate</th>
                        <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Avg Lat.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {explore.agents.map((agent) => (
                        <tr
                          key={agent.agent_id}
                          className="border-b hover:bg-muted/30 cursor-pointer transition-colors"
                          onClick={() => {
                            const params = new URLSearchParams({
                              start,
                              end,
                              agent_id: agent.agent_id,
                            })
                            if (outcome) params.set('outcome', outcome)
                            router.push(`/explore?${params.toString()}`)
                          }}
                        >
                          <td className="px-4 py-2.5 font-mono text-xs">{agent.agent_id}</td>
                          <td className="px-3 py-2.5 text-right">{agent.total.toLocaleString()}</td>
                          <td className="px-3 py-2.5 text-right text-red-600">{agent.denies}</td>
                          <td className="px-3 py-2.5">
                            <DenyRateBar rate={agent.deny_rate} />
                          </td>
                          <td className="px-4 py-2.5 text-right text-muted-foreground">{agent.avg_latency.toFixed(1)}ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Per-tool table */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">By Tool</CardTitle>
              <CardDescription className="text-xs">Activity breakdown per tool in this window</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {exploreLoading ? (
                <p className="text-sm text-muted-foreground p-4">Loading...</p>
              ) : !explore?.tools?.length ? (
                <p className="text-sm text-muted-foreground p-4">No tool data</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40">
                        <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Tool</th>
                        <th className="text-right px-3 py-2 text-xs font-medium text-muted-foreground">Calls</th>
                        <th className="text-right px-3 py-2 text-xs font-medium text-muted-foreground">Denied</th>
                        <th className="px-3 py-2 text-xs font-medium text-muted-foreground w-32">Deny Rate</th>
                        <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Avg Lat.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {explore.tools.map((tool) => (
                        <tr key={tool.tool_name} className="border-b hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-2.5 font-mono text-xs">{tool.tool_name}</td>
                          <td className="px-3 py-2.5 text-right">{tool.total.toLocaleString()}</td>
                          <td className="px-3 py-2.5 text-right text-red-600">{tool.denies}</td>
                          <td className="px-3 py-2.5">
                            <DenyRateBar rate={tool.deny_rate} />
                          </td>
                          <td className="px-4 py-2.5 text-right text-muted-foreground">{tool.avg_latency.toFixed(1)}ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Audit record list */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm">Audit Records</CardTitle>
                <CardDescription className="text-xs">
                  {recordsLoading ? 'Loading...' : `${records?.length ?? 0} records in this window — click to expand`}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {recordsLoading && (
              <p className="text-sm text-muted-foreground p-4">Loading records...</p>
            )}
            {!recordsLoading && records?.length === 0 && (
              <p className="text-sm text-muted-foreground p-4">No records found for this window.</p>
            )}
            <div className="divide-y max-h-[600px] overflow-y-auto">
              {records?.map((record) => (
                <div key={record.record_id}>
                  <div
                    className="px-4 py-3 hover:bg-muted/30 cursor-pointer transition-colors"
                    onClick={() =>
                      setExpandedRecordId(
                        expandedRecordId === record.record_id ? null : record.record_id
                      )
                    }
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <OutcomeBadge outcome={record.outcome} />
                        <code className="text-xs font-mono truncate">{record.tool_name}</code>
                        <span className="text-xs text-muted-foreground truncate hidden sm:block">
                          {record.agent_id}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 shrink-0 text-xs text-muted-foreground">
                        {record.latency_ms != null && (
                          <span>{record.latency_ms.toFixed(1)}ms</span>
                        )}
                        <span>{formatRelativeTime(record.timestamp)}</span>
                      </div>
                    </div>
                    {record.reason && (
                      <p className="text-xs text-muted-foreground mt-1 truncate">{record.reason}</p>
                    )}
                  </div>

                  {/* Inline expanded detail */}
                  {expandedRecordId === record.record_id && (
                    <div className="px-4 pb-4 bg-muted/20 border-t border-dashed space-y-3">
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 text-xs">
                        <div>
                          <p className="text-muted-foreground">Timestamp</p>
                          <p className="font-medium">{formatDate(record.timestamp)}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Agent</p>
                          <p className="font-mono">{record.agent_id}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Matched Rule</p>
                          <p className="font-mono truncate">{record.matched_rule || '—'}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Policy Version</p>
                          <p className="font-mono truncate">{record.policy_version || '—'}</p>
                        </div>
                      </div>

                      {record.reason && (
                        <div className="text-xs">
                          <p className="text-muted-foreground mb-0.5">Reason</p>
                          <p>{record.reason}</p>
                        </div>
                      )}

                      <div className="text-xs">
                        <p className="text-muted-foreground mb-0.5">Parameters</p>
                        <pre className="bg-muted p-2 rounded text-xs overflow-x-auto max-h-40">
                          {JSON.stringify(record.params, null, 2)}
                        </pre>
                      </div>

                      {record.execution_result && (
                        <div className="text-xs">
                          <p className="text-muted-foreground mb-0.5">Execution Result</p>
                          <pre className="bg-muted p-2 rounded text-xs overflow-x-auto max-h-40">
                            {JSON.stringify(record.execution_result, null, 2)}
                          </pre>
                        </div>
                      )}

                      {record.execution_error && (
                        <div className="text-xs">
                          <p className="text-muted-foreground mb-0.5">Execution Error</p>
                          <pre className="bg-destructive/10 text-destructive p-2 rounded text-xs overflow-x-auto">
                            {record.execution_error}
                          </pre>
                        </div>
                      )}

                      {record.escalation_id && (
                        <div className="text-xs">
                          <p className="text-muted-foreground mb-0.5">Escalation ID</p>
                          <p className="font-mono">{record.escalation_id}</p>
                          {record.resolved_by && (
                            <p className="mt-0.5">Resolved by {record.resolved_by}: {record.resolution}</p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default function ExplorePage() {
  return (
    <Suspense fallback={<div className="p-8 text-muted-foreground">Loading...</div>}>
      <ExplorePageInner />
    </Suspense>
  )
}
