'use client'

import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LiveFeed } from '@/components/LiveFeed'
import { MetricCard } from '@/components/MetricCard'
import { TimeRangePicker, type TimeRange } from '@/components/TimeRangePicker'
import { ThroughputChart, LatencyChart } from '@/components/TimeSeriesChart'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts'
import { useCustomer } from '@/app/providers'
import { useRouter } from 'next/navigation'

function buildDefaultRange(): TimeRange {
  const end = new Date()
  const start = new Date(end.getTime() - 60 * 60 * 1000)
  return { start: start.toISOString(), end: end.toISOString(), interval: '1m', label: '1h' }
}

export default function DashboardPage() {
  const { customerId } = useCustomer()
  const router = useRouter()
  const [timeRange, setTimeRange] = useState<TimeRange>(buildDefaultRange)

  const handleRangeChange = useCallback((r: TimeRange) => setTimeRange(r), [])

  const { data: metrics, isLoading } = useQuery({
    queryKey: ['metrics', customerId],
    queryFn: () => api.getMetricsSummary({ customer_id: customerId, period: '7d' }),
  })

  const { data: timeseries } = useQuery({
    queryKey: ['timeseries', customerId, timeRange.start, timeRange.end, timeRange.interval],
    queryFn: () =>
      api.getTimeseries({
        customer_id: customerId,
        start: timeRange.start,
        end: timeRange.end,
        interval: timeRange.interval,
      }),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading dashboard...</div>
      </div>
    )
  }

  const buckets = timeseries?.buckets || []

  const outcomeData = [
    { name: 'Allowed', outcome: 'allow', value: metrics?.allows || 0, fill: '#10b981' },
    { name: 'Denied', outcome: 'deny', value: metrics?.denies || 0, fill: '#ef4444' },
    { name: 'Escalated', outcome: 'escalate', value: metrics?.escalations || 0, fill: '#f59e0b' },
  ]

  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto px-4 py-8 space-y-8">
        {/* Time Range Picker */}
        <TimeRangePicker value={timeRange} onChange={handleRangeChange} />

        {/* Metrics Cards with Sparklines */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Total Calls"
            value={metrics?.total_calls || 0}
            subtitle="Last 7 days"
            color="text-foreground"
            sparklineData={buckets}
            sparklineKey="total"
            startTime={timeRange.start}
            endTime={timeRange.end}
          />
          <MetricCard
            title="Allowed"
            value={metrics?.allows || 0}
            subtitle={`${metrics?.total_calls ? ((metrics.allows / metrics.total_calls) * 100).toFixed(1) : 0}% of total`}
            color="text-green-600"
            sparklineData={buckets}
            sparklineKey="allows"
            drillDownOutcome="allow"
            startTime={timeRange.start}
            endTime={timeRange.end}
          />
          <MetricCard
            title="Denied"
            value={metrics?.denies || 0}
            subtitle={`${metrics?.total_calls ? ((metrics.denies / metrics.total_calls) * 100).toFixed(1) : 0}% of total`}
            color="text-red-600"
            sparklineData={buckets}
            sparklineKey="denies"
            drillDownOutcome="deny"
            startTime={timeRange.start}
            endTime={timeRange.end}
          />
          <MetricCard
            title="Escalations"
            value={metrics?.escalations || 0}
            subtitle={`${metrics?.total_calls ? ((metrics.escalations / metrics.total_calls) * 100).toFixed(1) : 0}% of total`}
            color="text-yellow-600"
            sparklineData={buckets}
            sparklineKey="escalations"
            drillDownOutcome="escalate"
            startTime={timeRange.start}
            endTime={timeRange.end}
          />
        </div>

        {/* Time-Series Charts */}
        <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-2">
          <ThroughputChart data={buckets} interval={timeRange.interval} rangeStart={timeRange.start} rangeEnd={timeRange.end} />
          <LatencyChart data={buckets} interval={timeRange.interval} rangeStart={timeRange.start} rangeEnd={timeRange.end} />
        </div>

        {/* Existing Charts — clickable */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Outcome Distribution</CardTitle>
              <CardDescription>Policy enforcement outcomes (last 7 days) — click a bar to explore</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={outcomeData}
                  style={{ cursor: 'pointer' }}
                  onClick={(e) => {
                    const outcome = e?.activePayload?.[0]?.payload?.outcome
                    if (!outcome) return
                    const params = new URLSearchParams({
                      start: timeRange.start,
                      end: timeRange.end,
                      outcome,
                    })
                    router.push(`/explore?${params.toString()}`)
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      return (
                        <div className="bg-card border rounded-lg p-3 shadow-lg text-sm">
                          <p className="font-medium">{payload[0].payload.name}: {payload[0].value}</p>
                          <p className="text-xs text-muted-foreground mt-1">Click to explore →</p>
                        </div>
                      )
                    }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {outcomeData.map((entry) => (
                      <Cell key={entry.name} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Top Tools</CardTitle>
              <CardDescription>Most frequently called tools — click a bar to explore</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={metrics?.top_tools || []}
                  layout="vertical"
                  style={{ cursor: 'pointer' }}
                  onClick={(e) => {
                    const toolName = e?.activePayload?.[0]?.payload?.tool
                    if (!toolName) return
                    const params = new URLSearchParams({
                      start: timeRange.start,
                      end: timeRange.end,
                    })
                    router.push(`/explore?${params.toString()}`)
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="tool" type="category" width={120} tick={{ fontSize: 12 }} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const d = payload[0].payload
                      return (
                        <div className="bg-card border rounded-lg p-3 shadow-lg text-sm">
                          <p className="font-medium">{d.tool}</p>
                          <p>Calls: {d.count}</p>
                          <p>Deny rate: {(d.deny_rate * 100).toFixed(1)}%</p>
                          <p className="text-xs text-muted-foreground mt-1">Click to explore →</p>
                        </div>
                      )
                    }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Top Denied Rules */}
        <Card>
          <CardHeader>
            <CardTitle>Top Denied Rules</CardTitle>
            <CardDescription>Rules that most frequently deny tool calls</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {metrics?.top_denied_rules.map((rule, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <Badge variant="destructive">{rule.count}</Badge>
                    <code className="text-sm">{rule.rule}</code>
                  </div>
                </div>
              ))}
              {(!metrics?.top_denied_rules || metrics.top_denied_rules.length === 0) && (
                <p className="text-sm text-muted-foreground">No denied rules in this period</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Latency Stats and Live Feed */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Policy Evaluation Latency</CardTitle>
              <CardDescription>Performance metrics</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">Average Latency</p>
                  <p className="text-2xl font-bold">{metrics?.latency.avg.toFixed(2)}ms</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Max Latency</p>
                  <p className="text-2xl font-bold">{metrics?.latency.max.toFixed(2)}ms</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <LiveFeed customerId={customerId} maxItems={5} />
        </div>
      </main>
    </div>
  )
}
