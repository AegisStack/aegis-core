'use client'

import { useRef, useState, useCallback, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import type { TimeseriesBucket } from '@/lib/api'
import {
  ComposedChart,
  Bar,
  Line,
  LineChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { ExternalLink, ZoomIn, X } from 'lucide-react'

// ── Palette ────────────────────────────────────────────────────────────────
const DD_GREEN  = '#1DB954'
const DD_RED    = '#E5473B'
const DD_AMBER  = '#F5A623'
const DD_BLUE   = '#4B87F5'
const DD_ORANGE = '#F0812A'
const DD_PURPLE = '#9B51E0'

const INTERVAL_MS: Record<string, number> = {
  '1m': 60_000, '5m': 300_000, '15m': 900_000, '1h': 3_600_000,
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  })
}

// ── Dark tooltip (shared) ─────────────────────────────────────────────────
function DarkTooltip({
  active, payload, label, unit = '',
}: {
  active?: boolean; payload?: any[]; label?: string; unit?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#111827', border: '1px solid #374151', borderRadius: 4,
      padding: '8px 12px', fontSize: 12, color: '#e5e7eb',
      minWidth: 160, boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
      pointerEvents: 'none',
    }}>
      <p style={{ fontWeight: 700, color: '#fff', marginBottom: 5, paddingBottom: 4, borderBottom: '1px solid #374151' }}>
        {label}
      </p>
      {payload.map((e: any) => (
        <div key={e.dataKey} style={{ display: 'flex', justifyContent: 'space-between', gap: 14, margin: '2px 0', color: e.color }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: e.color, display: 'inline-block' }} />
            {e.name}
          </span>
          <strong>
            {typeof e.value === 'number' ? e.value.toFixed(unit === 'ms' ? 1 : 0) : e.value}{unit}
          </strong>
        </div>
      ))}
      <p style={{ color: '#6b7280', marginTop: 5, fontSize: 11, paddingTop: 4, borderTop: '1px solid #374151' }}>
        Drag to select · click to explore
      </p>
    </div>
  )
}

// ── Drag-to-select hook ────────────────────────────────────────────────────
// Y-axis widths in our charts (left + right)
const LEFT_PAD  = 36   // left YAxis width
const RIGHT_PAD = 36   // right YAxis (throughput) or 5 (latency)

interface DragState {
  startPct: number
  endPct: number
  startIdx: number
  endIdx: number
}

function useDragSelect(
  chartData: any[],
  onZoom: (startIdx: number, endIdx: number) => void,
) {
  const containerRef = useRef<HTMLDivElement>(null)
  const dragStartX   = useRef<number | null>(null)
  const [drag, setDrag] = useState<DragState | null>(null)
  // stable ref so global callbacks always see latest value
  const dragRef      = useRef<DragState | null>(null)
  const isDragging   = useRef(false)
  const chartDataLen = useRef(chartData.length)
  chartDataLen.current = chartData.length

  const pctFromClientX = useCallback((clientX: number): number => {
    if (!containerRef.current) return 0
    const rect  = containerRef.current.getBoundingClientRect()
    const inner = rect.width - LEFT_PAD - RIGHT_PAD
    const rel   = clientX - rect.left - LEFT_PAD
    return Math.max(0, Math.min(1, rel / inner))
  }, [])

  const idxFromPct = useCallback(
    (pct: number) => Math.round(pct * Math.max(0, chartDataLen.current - 1)),
    [],
  )

  // Attach global mousemove/mouseup when dragging so cursor stays crosshair
  // even when pointer leaves the chart area.
  useEffect(() => {
    function handleMove(e: MouseEvent) {
      if (dragStartX.current === null) return
      const dist = Math.abs(e.clientX - dragStartX.current)
      if (dist > 4) {
        isDragging.current = true
        const startPct = pctFromClientX(dragStartX.current)
        const endPct   = pctFromClientX(e.clientX)
        const [lo, hi] = startPct < endPct ? [startPct, endPct] : [endPct, startPct]
        const next = { startPct: lo, endPct: hi, startIdx: idxFromPct(lo), endIdx: idxFromPct(hi) }
        dragRef.current = next
        setDrag(next)
      }
    }

    function handleUp(_e: MouseEvent) {
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      if (isDragging.current && dragRef.current) {
        onZoom(dragRef.current.startIdx, dragRef.current.endIdx)
      }
      dragStartX.current = null
      isDragging.current = false
      dragRef.current    = null
      setDrag(null)
    }

    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseup',   handleUp)
    return () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseup',   handleUp)
    }
  }, [pctFromClientX, idxFromPct, onZoom])

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return
    e.preventDefault()
    dragStartX.current = e.clientX
    isDragging.current = false
    document.body.style.cursor     = 'crosshair'
    document.body.style.userSelect = 'none'
  }, [])

  const clearDrag = useCallback(() => {
    setDrag(null)
    dragRef.current    = null
    dragStartX.current = null
    isDragging.current = false
    document.body.style.cursor     = ''
    document.body.style.userSelect = ''
  }, [])

  // Pixel positions for the selection overlay
  const selectionStyle = drag && containerRef.current ? {
    left:  LEFT_PAD + drag.startPct * (containerRef.current.getBoundingClientRect().width - LEFT_PAD - RIGHT_PAD),
    width: (drag.endPct - drag.startPct) * (containerRef.current.getBoundingClientRect().width - LEFT_PAD - RIGHT_PAD),
  } : null

  return { containerRef, drag, selectionStyle, onMouseDown, clearDrag, isDragging }
}

// ── Chart panel ────────────────────────────────────────────────────────────
function ChartPanel({
  title, subtitle, onExplore, children, zoomLabel, onZoom, onClearZoom,
}: {
  title: string; subtitle: string; onExplore: () => void; children: React.ReactNode
  zoomLabel?: string | null; onZoom?: () => void; onClearZoom?: () => void
}) {
  return (
    <div style={{
      background: 'var(--card)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '14px 16px 8px',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 6 }}>
        <div>
          <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>{title}</p>
          <p style={{ fontSize: 11, color: '#6b7280', margin: '2px 0 0' }}>{subtitle}</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          {zoomLabel && (
            <>
              <span style={{ fontSize: 11, background: 'rgba(75,135,245,0.12)', color: '#4B87F5', padding: '2px 8px', borderRadius: 10 }}>
                {zoomLabel}
              </span>
              <button onClick={onClearZoom} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6b7280', display: 'flex', alignItems: 'center', padding: 2 }} title="Clear">
                <X size={12} />
              </button>
              <button onClick={onZoom} style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, color: '#fff', background: '#4B87F5', border: 'none', borderRadius: 4, padding: '3px 8px', cursor: 'pointer', fontWeight: 600 }}>
                <ZoomIn size={11} /> Explore
              </button>
            </>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); onExplore() }}
            style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, color: '#4B87F5', background: 'none', border: 'none', cursor: 'pointer' }}
          >
            <ExternalLink size={11} /> Log Explorer
          </button>
        </div>
      </div>
      {children}
    </div>
  )
}

function EmptyState({ onExplore }: { onExplore: () => void }) {
  return (
    <div style={{ height: 230, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, color: '#6b7280', fontSize: 13 }}>
      <span>No data for this time range</span>
      <button onClick={onExplore} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: 'var(--secondary)', border: '1px solid var(--border)', borderRadius: 4, cursor: 'pointer', fontSize: 12, color: 'var(--foreground)' }}>
        <ExternalLink size={13} /> Open Log Explorer
      </button>
    </div>
  )
}

function LoadingState() {
  return (
    <div style={{ height: 230, padding: '12px 0', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 4 }}>
      {/* Fake axis line */}
      <div className="animate-pulse" style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 180, paddingLeft: 38 }}>
        {Array.from({ length: 28 }).map((_, i) => (
          <div
            key={i}
            className="bg-muted rounded-sm"
            style={{
              flex: 1,
              height: `${20 + Math.abs(Math.sin(i * 0.7 + 1)) * 70 + Math.abs(Math.sin(i * 1.3)) * 40}%`,
              opacity: 0.5 + (i % 3) * 0.15,
            }}
          />
        ))}
      </div>
      {/* Fake x-axis */}
      <div className="animate-pulse bg-muted rounded" style={{ height: 8, marginLeft: 38, marginRight: 8, opacity: 0.3 }} />
    </div>
  )
}

// ── Throughput chart ───────────────────────────────────────────────────────
export interface ThroughputChartProps {
  data: TimeseriesBucket[]
  interval: string
  rangeStart?: string
  rangeEnd?: string
  onRangeSelect?: (start: string, end: string, interval: string) => void
  isLoading?: boolean
}

export function ThroughputChart({ data, interval, rangeStart, rangeEnd, onRangeSelect, isLoading }: ThroughputChartProps) {
  const router = useRouter()
  const hoveredBucket  = useRef<TimeseriesBucket | null>(null)
  const [onBar, setOnBar] = useState(false)
  const leaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  function barEnter() {
    if (leaveTimer.current) clearTimeout(leaveTimer.current)
    setOnBar(true)
  }
  function barLeave() {
    // small delay so moving between stacked segments doesn't flicker
    leaveTimer.current = setTimeout(() => setOnBar(false), 80)
  }

  const chartData = data.map((b) => ({ ...b, t: fmtTime(b.time), total: b.allows + b.denies + b.escalations }))

  function fallbackUrl() {
    return `/explore?${new URLSearchParams({ start: rangeStart || '', end: rangeEnd || '' })}`
  }

  const handleZoom = useCallback((startIdx: number, endIdx: number) => {
    if (!chartData[startIdx] || !chartData[endIdx]) return
    const start = chartData[startIdx].time
    const end   = new Date(new Date(chartData[endIdx].time).getTime() + (INTERVAL_MS[interval] || 60_000)).toISOString()
    if (onRangeSelect) onRangeSelect(start, end, '1m')
    else router.push(`/explore?${new URLSearchParams({ start, end })}`)
  }, [chartData, interval, onRangeSelect, router])

  const { containerRef, drag, selectionStyle, onMouseDown, clearDrag, isDragging } = useDragSelect(chartData, handleZoom)

  const zoomLabel = drag && chartData[drag.startIdx] && chartData[drag.endIdx]
    ? `${chartData[drag.startIdx].t} – ${chartData[drag.endIdx].t}` : null

  const barSize = Math.max(3, Math.min(18, Math.floor(560 / (chartData.length || 1)) - 1))

  return (
    <ChartPanel
      title="Throughput"
      subtitle={`Stacked outcomes per ${interval} · drag to select · click to explore`}
      onExplore={() => router.push(fallbackUrl())}
      zoomLabel={zoomLabel}
      onZoom={() => {}}
      onClearZoom={clearDrag}
    >
      {isLoading
        ? <LoadingState />
        : chartData.length === 0
        ? <EmptyState onExplore={() => router.push(fallbackUrl())} />
        : (
          <div
            ref={containerRef}
            className="chart-crosshair"
            style={{ position: 'relative', userSelect: 'none' }}
            onMouseDown={onMouseDown}
            onClick={() => {
              if (isDragging.current) return
              const b = hoveredBucket.current
              router.push(b
                ? `/explore?${new URLSearchParams({ start: b.time, end: new Date(new Date(b.time).getTime() + (INTERVAL_MS[interval] || 60_000)).toISOString() })}`
                : fallbackUrl())
            }}
            onMouseLeave={() => { hoveredBucket.current = null }}
          >
            {/* Selection overlay */}
            {selectionStyle && (
              <div
                style={{
                  position: 'absolute',
                  top: 0, bottom: 0,
                  left: selectionStyle.left,
                  width: selectionStyle.width,
                  background: 'rgba(75,135,245,0.15)',
                  border: '1px solid rgba(75,135,245,0.5)',
                  borderRadius: 2,
                  pointerEvents: 'none',
                  zIndex: 5,
                }}
              />
            )}

            <ResponsiveContainer width="100%" height={230}>
              <ComposedChart
                data={chartData}
                barSize={barSize}
                barCategoryGap={1}
                onMouseMove={(e) => { if (e?.activePayload?.[0]) hoveredBucket.current = e.activePayload[0].payload }}
              >
                <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.4} />
                <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                <YAxis yAxisId="left"  tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} width={LEFT_PAD} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} width={RIGHT_PAD} />
                <Tooltip
                  content={(p) => onBar ? <DarkTooltip active={p.active} payload={p.payload} label={p.label} /> : null}
                  cursor={{ fill: 'rgba(255,255,255,0.04)', stroke: 'rgba(255,255,255,0.12)', strokeWidth: 1 }}
                  isAnimationActive={false}
                />
                <Legend iconType="square" iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
                <Bar yAxisId="left" dataKey="allows"      name="Allowed"   stackId="s" fill={DD_GREEN} onMouseEnter={barEnter} onMouseLeave={barLeave} />
                <Bar yAxisId="left" dataKey="denies"      name="Denied"    stackId="s" fill={DD_RED}   onMouseEnter={barEnter} onMouseLeave={barLeave} />
                <Bar yAxisId="left" dataKey="escalations" name="Escalated" stackId="s" fill={DD_AMBER} radius={[2, 2, 0, 0]} onMouseEnter={barEnter} onMouseLeave={barLeave} />
                <Line yAxisId="right" type="monotone" dataKey="total" stroke="#fff" strokeOpacity={0.25} strokeWidth={1.5} dot={false} legendType="none" activeDot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )
      }
    </ChartPanel>
  )
}

// ── Latency chart ──────────────────────────────────────────────────────────
export interface LatencyChartProps {
  data: TimeseriesBucket[]
  interval: string
  rangeStart?: string
  rangeEnd?: string
  onRangeSelect?: (start: string, end: string, interval: string) => void
  isLoading?: boolean
}

export function LatencyChart({ data, interval, rangeStart, rangeEnd, onRangeSelect, isLoading }: LatencyChartProps) {
  const router = useRouter()
  const hoveredBucket = useRef<TimeseriesBucket | null>(null)
  const [onLine, setOnLine] = useState(false)
  const lineLeaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  function dotEnter() {
    if (lineLeaveTimer.current) clearTimeout(lineLeaveTimer.current)
    setOnLine(true)
  }
  function dotLeave() {
    lineLeaveTimer.current = setTimeout(() => setOnLine(false), 80)
  }

  const chartData = data.map((b) => ({ ...b, t: fmtTime(b.time) }))

  function fallbackUrl() {
    return `/explore?${new URLSearchParams({ start: rangeStart || '', end: rangeEnd || '' })}`
  }

  const handleZoom = useCallback((startIdx: number, endIdx: number) => {
    if (!chartData[startIdx] || !chartData[endIdx]) return
    const start = chartData[startIdx].time
    const end   = new Date(new Date(chartData[endIdx].time).getTime() + (INTERVAL_MS[interval] || 60_000)).toISOString()
    if (onRangeSelect) onRangeSelect(start, end, '1m')
    else router.push(`/explore?${new URLSearchParams({ start, end })}`)
  }, [chartData, interval, onRangeSelect, router])

  const { containerRef, drag, selectionStyle, onMouseDown, clearDrag, isDragging } = useDragSelect(chartData, handleZoom)

  const avgP95 = chartData.length
    ? chartData.reduce((s, b) => s + (b.p95_latency || 0), 0) / chartData.length : 0

  const zoomLabel = drag && chartData[drag.startIdx] && chartData[drag.endIdx]
    ? `${chartData[drag.startIdx].t} – ${chartData[drag.endIdx].t}` : null

  return (
    <ChartPanel
      title="Latency"
      subtitle={`Avg / P95 / P99 per ${interval} · drag to select · click to explore`}
      onExplore={() => router.push(fallbackUrl())}
      zoomLabel={zoomLabel}
      onZoom={() => {}}
      onClearZoom={clearDrag}
    >
      {isLoading
        ? <LoadingState />
        : chartData.length === 0
        ? <EmptyState onExplore={() => router.push(fallbackUrl())} />
        : (
          <div
            ref={containerRef}
            className="chart-crosshair"
            style={{ position: 'relative', userSelect: 'none' }}
            onMouseDown={onMouseDown}
            onClick={() => {
              if (isDragging.current) return
              const b = hoveredBucket.current
              router.push(b
                ? `/explore?${new URLSearchParams({ start: b.time, end: new Date(new Date(b.time).getTime() + (INTERVAL_MS[interval] || 60_000)).toISOString() })}`
                : fallbackUrl())
            }}
            onMouseLeave={() => { hoveredBucket.current = null }}
          >
            {/* Selection overlay */}
            {selectionStyle && (
              <div
                style={{
                  position: 'absolute',
                  top: 0, bottom: 0,
                  left: selectionStyle.left,
                  width: selectionStyle.width,
                  background: 'rgba(75,135,245,0.15)',
                  border: '1px solid rgba(75,135,245,0.5)',
                  borderRadius: 2,
                  pointerEvents: 'none',
                  zIndex: 5,
                }}
              />
            )}

            <ResponsiveContainer width="100%" height={230}>
              <LineChart
                data={chartData}
                onMouseMove={(e) => { if (e?.activePayload?.[0]) hoveredBucket.current = e.activePayload[0].payload }}
              >
                <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.4} />
                <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} width={LEFT_PAD} unit="ms" />
                {avgP95 > 0 && (
                  <ReferenceLine y={avgP95} stroke={DD_AMBER} strokeDasharray="4 3" strokeOpacity={0.5}
                    label={{ value: 'p95 avg', fontSize: 9, fill: DD_AMBER, position: 'insideTopRight' }}
                  />
                )}
                <Tooltip
                  content={(p) => onLine ? <DarkTooltip active={p.active} payload={p.payload} label={p.label} unit="ms" /> : null}
                  cursor={{ stroke: 'rgba(255,255,255,0.3)', strokeWidth: 1, strokeDasharray: '4 3' }}
                  isAnimationActive={false}
                />
                <Legend iconType="plainline" iconSize={18} wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
                <Line type="monotone" dataKey="avg_latency" name="Avg" stroke={DD_BLUE}   strokeWidth={2}   dot={false} activeDot={{ r: 4, stroke: DD_BLUE,   strokeWidth: 2, fill: '#111827', onMouseOver: dotEnter, onMouseOut: dotLeave }} />
                <Line type="monotone" dataKey="p95_latency" name="P95" stroke={DD_ORANGE} strokeWidth={1.5} dot={false} strokeDasharray="5 3" activeDot={{ r: 3, stroke: DD_ORANGE, fill: '#111827', onMouseOver: dotEnter, onMouseOut: dotLeave }} />
                <Line type="monotone" dataKey="p99_latency" name="P99" stroke={DD_PURPLE} strokeWidth={1.5} dot={false} strokeDasharray="3 3" activeDot={{ r: 3, stroke: DD_PURPLE, fill: '#111827', onMouseOver: dotEnter, onMouseOut: dotLeave }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )
      }
    </ChartPanel>
  )
}
