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
import { ThroughputChart, LatencyChart } from '@/components/TimeSeriesChart'
import { ArrowLeft, ShieldCheck, ShieldX, AlertTriangle, Timer } from 'lucide-react'

function buildDefaultRange(): { start: string; end: string } {
  const end = new Date()
  const start = new Date(end.getTime() - 60 * 60 * 1000)
  return { start: start.toISOString(), end: end.toISOString() }
}

function OutcomeBadge({ outcome }: { outcome: string }) {
  switch (outcome) {
    case 'allow':    return <Badge variant="success">Allow</Badge>
    case 'deny':     return <Badge variant="destructive">Deny</Badge>
    case 'escalate': return <Badge variant="warning">Escalate</Badge>
    default:         return <Badge>{outcome}</Badge>
  }
}

function DenyRateBar({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100)
  const color = pct > 50 ? '#E5473B' : pct > 20 ? '#F5A623' : '#1DB954'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs w-8 text-right font-mono" style={{ color }}>{pct}%</span>
    </div>
  )
}

// Inline interval selector for the explore page charts
function intervalFor(start: string, end: string): string {
  const diffMin = (new Date(end).getTime() - new Date(start).getTime()) / 60_000
  if (diffMin <= 60)   return '1m'
  if (diffMin <= 720)  return '5m'
  if (diffMin <= 2880) return '15m'
  return '1h'
}

function ExplorePageInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { customerId } = useCustomer()

  const defaults = buildDefaultRange()
  const outcome = searchParams.get('outcome') || ''
  const agentId = searchParams.get('agent_id') || ''

  const [timeRange, setTimeRange] = useState<TimeRange>(() => ({
    start:    searchParams.get('start') || defaults.start,
    end:      searchParams.get('end')   || defaults.end,
    interval: '1m',
    label:    searchParams.get('start') ? 'custom' : '1h',
  }))

  const [expandedRecordId, setExpandedRecordId] = useState<string | null>(null)

  const { start, end } = timeRange
  const interval = intervalFor(start, end)

  // ── Data queries ────────────────────────────────────────────────────────────
  const { data: explore, isLoading: exploreLoading } = useQuery({
    queryKey: ['explore', customerId, start, end, outcome, agentId],
    queryFn: () => api.getExplore({
      customer_id: customerId, start, end,
      outcome: outcome || undefined,
      agent_id: agentId || undefined,
    }),
    enabled: !!(customerId && start && end),
  })

  const { data: timeseries, isLoading: timeseriesLoading } = useQuery({
    queryKey: ['explore-timeseries', customerId, start, end, interval, outcome, agentId],
    queryFn: () => api.getTimeseries({
      customer_id: customerId, start, end, interval,
      agent_id: agentId || undefined,
    }),
    enabled: !!(customerId && start && end),
  })

  const { data: records, isLoading: recordsLoading } = useQuery({
    queryKey: ['explore-records', customerId, start, end, outcome, agentId],
    queryFn: () => api.getAuditRecords({
      customer_id: customerId,
      start_time: start, end_time: end,
      outcome: outcome || undefined,
      agent_id: agentId || undefined,
      limit: 200,
    }),
    enabled: !!(customerId && start && end),
  })

  const summary = explore?.summary
  const buckets = timeseries?.buckets || []

  // Brush zoom handler -- zooms the explore page in place
  function handleRangeSelect(s: string, e: string, iv: string) {
    setTimeRange({ start: s, end: e, interval: iv, label: 'custom' })
  }

  return (
    <div className="min-h-screen bg-background">
      {/* ── Sticky header ─────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-20 border-b bg-card/95 backdrop-blur px-6 py-3 space-y-3">
        {/* Row 1: back + title + filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors shrink-0"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>

          <h1 className="text-base font-semibold">Log Explorer</h1>

          {outcome && <OutcomeBadge outcome={outcome} />}
          {agentId && (
            <span className="text-xs bg-muted px-2 py-0.5 rounded font-mono">{agentId}</span>
          )}
        </div>

        {/* Row 2: time range picker */}
        <TimeRangePicker value={timeRange} onChange={setTimeRange} />

        {/* Row 3: summary stat bar */}
        {summary && (
          <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
            {[
              { label: 'Total',     value: summary.total.toLocaleString(),         icon: null,          bg: 'bg-muted/50',        text: '' },
              { label: 'Allowed',   value: summary.allows.toLocaleString(),         icon: <ShieldCheck className="h-3.5 w-3.5 text-green-500" />,  bg: 'bg-green-500/10', text: 'text-green-600' },
              { label: 'Denied',    value: summary.denies.toLocaleString(),         icon: <ShieldX className="h-3.5 w-3.5 text-red-500" />,    bg: 'bg-red-500/10',   text: 'text-red-600'   },
              { label: 'Escalated', value: summary.escalations.toLocaleString(),    icon: <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />, bg: 'bg-amber-500/10', text: 'text-amber-600' },
              { label: 'Avg',       value: `${summary.avg_latency.toFixed(1)}ms`,   icon: <Timer className="h-3.5 w-3.5 text-blue-500" />,   bg: 'bg-blue-500/10',  text: 'text-blue-600'  },
              { label: 'P95',       value: `${summary.p95_latency.toFixed(1)}ms`,   icon: null,          bg: 'bg-muted/50',        text: '' },
              { label: 'P99',       value: `${summary.p99_latency.toFixed(1)}ms`,   icon: null,          bg: 'bg-muted/50',        text: '' },
            ].map(({ label, value, icon, bg, text }) => (
              <div key={label} className={`${bg} rounded-md px-2 py-1.5 flex items-center gap-1.5`}>
                {icon}
                <div>
                  <p className="text-[10px] text-muted-foreground leading-none">{label}</p>
                  <p className={`text-sm font-bold leading-tight mt-0.5 ${text}`}>{value}</p>
                </div>
              </div>
            ))}
          </div>
        )}
        {exploreLoading && !summary && (
          <p className="text-xs text-muted-foreground">Loading summary...</p>
        )}
      </div>

      <div className="px-6 py-5 space-y-5">
        {/* ── Timeseries charts (same as Overview, with brush zoom) ─────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ThroughputChart
            data={buckets}
            interval={interval}
            rangeStart={start}
            rangeEnd={end}
            isLoading={timeseriesLoading}
            onRangeSelect={handleRangeSelect}
          />
          <LatencyChart
            data={buckets}
            interval={interval}
            rangeStart={start}
            rangeEnd={end}
            isLoading={timeseriesLoading}
            onRangeSelect={handleRangeSelect}
          />
        </div>

        {/* ── Breakdown tables ──────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* By Agent */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">By Agent</CardTitle>
              <CardDescription className="text-xs">Click a row to filter to that agent</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {exploreLoading ? (
                <p className="text-xs text-muted-foreground p-4">Loading...</p>
              ) : !explore?.agents?.length ? (
                <p className="text-xs text-muted-foreground p-4">No agent data</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40">
                        <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Agent</th>
                        <th className="text-right px-3 py-2 text-xs font-medium text-muted-foreground">Calls</th>
                        <th className="text-right px-3 py-2 text-xs font-medium text-muted-foreground">Denied</th>
                        <th className="px-3 py-2 text-xs font-medium text-muted-foreground w-28">Deny Rate</th>
                        <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Avg Lat.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {explore.agents.map((agent) => (
                        <tr
                          key={agent.agent_id}
                          className="border-b hover:bg-muted/30 cursor-pointer transition-colors"
                          onClick={() => {
                            const p = new URLSearchParams({ start, end, agent_id: agent.agent_id })
                            if (outcome) p.set('outcome', outcome)
                            router.push(`/explore?${p.toString()}`)
                          }}
                        >
                          <td className="px-4 py-2 font-mono text-xs">{agent.agent_id}</td>
                          <td className="px-3 py-2 text-right">{agent.total.toLocaleString()}</td>
                          <td className="px-3 py-2 text-right" style={{ color: '#E5473B' }}>{agent.denies}</td>
                          <td className="px-3 py-2"><DenyRateBar rate={agent.deny_rate} /></td>
                          <td className="px-4 py-2 text-right text-muted-foreground text-xs">{agent.avg_latency.toFixed(1)}ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* By Tool */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">By Tool</CardTitle>
              <CardDescription className="text-xs">Breakdown per tool in this window</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {exploreLoading ? (
                <p className="text-xs text-muted-foreground p-4">Loading...</p>
              ) : !explore?.tools?.length ? (
                <p className="text-xs text-muted-foreground p-4">No tool data</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40">
                        <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Tool</th>
                        <th className="text-right px-3 py-2 text-xs font-medium text-muted-foreground">Calls</th>
                        <th className="text-right px-3 py-2 text-xs font-medium text-muted-foreground">Denied</th>
                        <th className="px-3 py-2 text-xs font-medium text-muted-foreground w-28">Deny Rate</th>
                        <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Avg Lat.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {explore.tools.map((tool) => (
                        <tr key={tool.tool_name} className="border-b hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-2 font-mono text-xs">{tool.tool_name}</td>
                          <td className="px-3 py-2 text-right">{tool.total.toLocaleString()}</td>
                          <td className="px-3 py-2 text-right" style={{ color: '#E5473B' }}>{tool.denies}</td>
                          <td className="px-3 py-2"><DenyRateBar rate={tool.deny_rate} /></td>
                          <td className="px-4 py-2 text-right text-muted-foreground text-xs">{tool.avg_latency.toFixed(1)}ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── Audit record list ─────────────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Audit Records</CardTitle>
            <CardDescription className="text-xs">
              {recordsLoading
                ? 'Loading...'
                : `${records?.length ?? 0} records in this window — click to expand`}
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {recordsLoading && <p className="text-xs text-muted-foreground p-4">Loading records...</p>}
            {!recordsLoading && records?.length === 0 && (
              <p className="text-xs text-muted-foreground p-4">No records found for this window.</p>
            )}
            <div className="divide-y max-h-[600px] overflow-y-auto">
              {records?.map((record) => (
                <div key={record.record_id}>
                  <div
                    className="px-4 py-3 hover:bg-muted/30 cursor-pointer transition-colors"
                    onClick={() =>
                      setExpandedRecordId(expandedRecordId === record.record_id ? null : record.record_id)
                    }
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <OutcomeBadge outcome={record.outcome} />
                        <code className="text-xs font-mono truncate">{record.tool_name}</code>
                        <span className="text-xs text-muted-foreground truncate hidden sm:block">{record.agent_id}</span>
                      </div>
                      <div className="flex items-center gap-3 shrink-0 text-xs text-muted-foreground">
                        {record.latency_ms != null && <span>{record.latency_ms.toFixed(1)}ms</span>}
                        <span>{formatRelativeTime(record.timestamp)}</span>
                      </div>
                    </div>
                    {record.reason && (
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">{record.reason}</p>
                    )}
                  </div>

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
    <Suspense fallback={<div className="p-8 text-muted-foreground text-sm">Loading...</div>}>
      <ExplorePageInner />
    </Suspense>
  )
}
