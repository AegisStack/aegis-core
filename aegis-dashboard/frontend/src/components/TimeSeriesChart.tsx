'use client'

import { useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { TimeseriesBucket } from '@/lib/api'
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { ExternalLink } from 'lucide-react'

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

const INTERVAL_MS: Record<string, number> = {
  '1m': 60_000,
  '5m': 300_000,
  '15m': 900_000,
  '1h': 3_600_000,
}

interface ThroughputChartProps {
  data: TimeseriesBucket[]
  interval: string
  /** Full time range start — used for the "View in Explorer" fallback */
  rangeStart?: string
  rangeEnd?: string
}

export function ThroughputChart({ data, interval, rangeStart, rangeEnd }: ThroughputChartProps) {
  const router = useRouter()
  const hoveredBucket = useRef<TimeseriesBucket | null>(null)

  const chartData = data.map((b) => ({ ...b, timeLabel: formatTime(b.time) }))

  function buildExploreUrl(bucket: TimeseriesBucket | null, outcome?: string): string {
    const base = bucket
      ? { start: bucket.time, end: new Date(new Date(bucket.time).getTime() + (INTERVAL_MS[interval] || 60_000)).toISOString() }
      : { start: rangeStart || '', end: rangeEnd || '' }
    const params = new URLSearchParams(base)
    if (outcome) params.set('outcome', outcome)
    return `/explore?${params.toString()}`
  }

  function handleChartClick() {
    router.push(buildExploreUrl(hoveredBucket.current))
  }

  function handleMouseMove(e: any) {
    if (e?.activePayload?.[0]) {
      hoveredBucket.current = e.activePayload[0].payload as TimeseriesBucket
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle>Throughput Over Time</CardTitle>
            <CardDescription>
              Policy evaluation outcomes per {interval} bucket
            </CardDescription>
          </div>
          <button
            onClick={() => router.push(buildExploreUrl(null))}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0 mt-0.5"
            title="Open full range in Log Explorer"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Log Explorer
          </button>
        </div>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[300px] gap-3 text-muted-foreground">
            <p className="text-sm">No data for this time range</p>
            {(rangeStart && rangeEnd) && (
              <button
                onClick={() => router.push(buildExploreUrl(null))}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Open Log Explorer
              </button>
            )}
          </div>
        ) : (
          <div
            className="cursor-pointer"
            onClick={handleChartClick}
            title="Click to drill down into this time bucket"
          >
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart
                data={chartData}
                onMouseMove={handleMouseMove}
                onMouseLeave={() => { hoveredBucket.current = null }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timeLabel" tick={{ fontSize: 12 }} />
                <YAxis />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null
                    return (
                      <div className="bg-card border rounded-lg p-3 shadow-lg text-sm">
                        <p className="font-medium mb-1">{label}</p>
                        {payload.map((entry: any) => (
                          <p key={entry.dataKey} style={{ color: entry.color }}>
                            {entry.name}: {entry.value}
                          </p>
                        ))}
                        <p className="text-xs text-muted-foreground mt-1.5 border-t pt-1">Click to drill down →</p>
                      </div>
                    )
                  }}
                />
                <Legend />
                <Area type="monotone" dataKey="allows" name="Allowed" stackId="1" stroke="#22c55e" fill="#22c55e" fillOpacity={0.6} />
                <Area type="monotone" dataKey="denies" name="Denied" stackId="1" stroke="#ef4444" fill="#ef4444" fillOpacity={0.6} />
                <Area type="monotone" dataKey="escalations" name="Escalated" stackId="1" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.6} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface LatencyChartProps {
  data: TimeseriesBucket[]
  interval: string
  rangeStart?: string
  rangeEnd?: string
}

export function LatencyChart({ data, interval, rangeStart, rangeEnd }: LatencyChartProps) {
  const router = useRouter()
  const hoveredBucket = useRef<TimeseriesBucket | null>(null)

  const chartData = data.map((b) => ({ ...b, timeLabel: formatTime(b.time) }))

  function buildExploreUrl(bucket: TimeseriesBucket | null): string {
    const base = bucket
      ? { start: bucket.time, end: new Date(new Date(bucket.time).getTime() + (INTERVAL_MS[interval] || 60_000)).toISOString() }
      : { start: rangeStart || '', end: rangeEnd || '' }
    return `/explore?${new URLSearchParams(base).toString()}`
  }

  function handleChartClick() {
    router.push(buildExploreUrl(hoveredBucket.current))
  }

  function handleMouseMove(e: any) {
    if (e?.activePayload?.[0]) {
      hoveredBucket.current = e.activePayload[0].payload as TimeseriesBucket
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle>Latency Over Time</CardTitle>
            <CardDescription>
              Evaluation latency percentiles per {interval} bucket
            </CardDescription>
          </div>
          <button
            onClick={() => router.push(buildExploreUrl(null))}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0 mt-0.5"
            title="Open full range in Log Explorer"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Log Explorer
          </button>
        </div>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[300px] gap-3 text-muted-foreground">
            <p className="text-sm">No data for this time range</p>
            {(rangeStart && rangeEnd) && (
              <button
                onClick={() => router.push(buildExploreUrl(null))}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Open Log Explorer
              </button>
            )}
          </div>
        ) : (
          <div
            className="cursor-pointer"
            onClick={handleChartClick}
            title="Click to drill down into this time bucket"
          >
            <ResponsiveContainer width="100%" height={300}>
              <LineChart
                data={chartData}
                onMouseMove={handleMouseMove}
                onMouseLeave={() => { hoveredBucket.current = null }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timeLabel" tick={{ fontSize: 12 }} />
                <YAxis unit="ms" />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null
                    return (
                      <div className="bg-card border rounded-lg p-3 shadow-lg text-sm">
                        <p className="font-medium mb-1">{label}</p>
                        {payload.map((entry: any) => (
                          <p key={entry.dataKey} style={{ color: entry.color }}>
                            {entry.name}: {entry.value?.toFixed(2)}ms
                          </p>
                        ))}
                        <p className="text-xs text-muted-foreground mt-1.5 border-t pt-1">Click to drill down →</p>
                      </div>
                    )
                  }}
                />
                <Legend />
                <Line type="monotone" dataKey="avg_latency" name="Avg" stroke="#3b82f6" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="p95_latency" name="P95" stroke="#f59e0b" dot={false} strokeWidth={2} strokeDasharray="5 5" />
                <Line type="monotone" dataKey="p99_latency" name="P99" stroke="#ef4444" dot={false} strokeWidth={2} strokeDasharray="3 3" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
