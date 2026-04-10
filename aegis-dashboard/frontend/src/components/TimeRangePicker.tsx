'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import { Calendar, RefreshCw, ChevronDown, Circle } from 'lucide-react'

export interface TimeRange {
  start: string
  end: string
  interval: string
  label: string
}

export const PRESETS: { label: string; display: string; minutes: number; interval: string }[] = [
  { label: '15m', display: 'Past 15 minutes', minutes: 15,    interval: '1m'  },
  { label: '1h',  display: 'Past hour',        minutes: 60,    interval: '1m'  },
  { label: '4h',  display: 'Past 4 hours',     minutes: 240,   interval: '5m'  },
  { label: '1d',  display: 'Past day',          minutes: 1440,  interval: '15m' },
  { label: '7d',  display: 'Past week',         minutes: 10080, interval: '1h'  },
]

export function buildRange(minutes: number, interval: string, label: string): TimeRange {
  const end = new Date()
  const start = new Date(end.getTime() - minutes * 60 * 1000)
  return { start: start.toISOString(), end: end.toISOString(), interval, label }
}

function toDatetimeLocal(iso: string): string {
  return iso.slice(0, 16)
}

function fmtRangeLabel(range: TimeRange): string {
  if (range.label !== 'custom') {
    const preset = PRESETS.find((p) => p.label === range.label)
    return preset ? preset.display : `Last ${range.label}`
  }
  const fmt = (iso: string) =>
    new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false,
    })
  return `${fmt(range.start)} → ${fmt(range.end)}`
}

interface TimeRangePickerProps {
  value: TimeRange
  onChange: (range: TimeRange) => void
}

export function TimeRangePicker({ value, onChange }: TimeRangePickerProps) {
  const [open, setOpen] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [customFrom, setCustomFrom] = useState(toDatetimeLocal(value.start))
  const [customTo, setCustomTo]     = useState(toDatetimeLocal(value.end))
  const triggerRef  = useRef<HTMLButtonElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0 })

  // Close on outside click
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (
        dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
        triggerRef.current  && !triggerRef.current.contains(e.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [])

  const refresh = useCallback(() => {
    const p = PRESETS.find((pr) => pr.label === value.label)
    if (p) onChange(buildRange(p.minutes, p.interval, p.label))
  }, [value.label, onChange])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(refresh, 30_000)
    return () => clearInterval(id)
  }, [autoRefresh, refresh])

  function applyPreset(p: (typeof PRESETS)[number]) {
    onChange(buildRange(p.minutes, p.interval, p.label))
    setOpen(false)
  }

  function applyCustom() {
    if (!customFrom || !customTo) return
    const start = new Date(customFrom).toISOString()
    const end   = new Date(customTo).toISOString()
    if (start >= end) return
    const diffMin = (new Date(end).getTime() - new Date(start).getTime()) / 60_000
    const interval = diffMin <= 60 ? '1m' : diffMin <= 720 ? '5m' : diffMin <= 2880 ? '15m' : '1h'
    onChange({ start, end, interval, label: 'custom' })
    setOpen(false)
  }

  return (
    <div className="flex items-center gap-2" style={{ position: 'relative' }}>
      {/* Main pill — triggers dropdown */}
      <button
        ref={triggerRef}
        onClick={() => {
          if (triggerRef.current) {
            const r = triggerRef.current.getBoundingClientRect()
            setDropdownPos({ top: r.bottom + 6, left: r.left })
          }
          setOpen((o) => !o)
        }}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border bg-card text-foreground text-xs font-medium hover:bg-muted transition-colors whitespace-nowrap"
      >
        <Calendar size={13} className="text-blue-500 shrink-0" />
        {fmtRangeLabel(value)}
        <ChevronDown size={11} className="text-muted-foreground ml-1" />
      </button>

      {/* Refresh */}
      <button
        onClick={refresh}
        title="Refresh now"
        className="flex items-center justify-center w-7 h-7 rounded-md border bg-card text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
      >
        <RefreshCw size={12} />
      </button>

      {/* Live toggle */}
      <button
        onClick={() => setAutoRefresh((a) => !a)}
        title={autoRefresh ? 'Stop live updates' : 'Enable live updates (30s)'}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border text-xs font-medium transition-colors ${
          autoRefresh
            ? 'border-green-500 bg-green-500/10 text-green-500'
            : 'border-border bg-card text-muted-foreground hover:bg-muted'
        }`}
      >
        <Circle
          size={7}
          fill={autoRefresh ? '#1DB954' : 'transparent'}
          stroke={autoRefresh ? '#1DB954' : 'currentColor'}
        />
        Live
      </button>

      {/* Dropdown — portalled to document.body to escape any stacking context */}
      {open && typeof document !== 'undefined' && createPortal(
        <div
          ref={dropdownRef}
          style={{
            position: 'fixed',
            top: dropdownPos.top,
            left: dropdownPos.left,
            zIndex: 9999,
            width: 290,
          }}
          className="rounded-lg border bg-popover shadow-xl overflow-hidden"
        >
          {/* Quick ranges */}
          <div className="border-b">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest px-3.5 pt-3 pb-1.5">
              Quick ranges
            </p>
            {PRESETS.map((p) => (
              <button
                key={p.label}
                onClick={() => applyPreset(p)}
                className={`flex items-center justify-between w-full text-left px-3.5 py-2 text-sm transition-colors ${
                  value.label === p.label
                    ? 'bg-blue-500/10 text-blue-500 font-semibold'
                    : 'text-foreground hover:bg-muted'
                }`}
              >
                <span>{p.display}</span>
                <span className="text-[11px] text-muted-foreground ml-2">{p.label}</span>
              </button>
            ))}
          </div>

          {/* Custom range */}
          <div className="p-3.5 space-y-3">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
              Custom range
            </p>
            <label className="block space-y-1">
              <span className="text-xs text-muted-foreground">From</span>
              <input
                type="datetime-local"
                value={customFrom}
                onChange={(e) => setCustomFrom(e.target.value)}
                className="w-full px-2 py-1.5 text-xs rounded border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </label>
            <label className="block space-y-1">
              <span className="text-xs text-muted-foreground">To</span>
              <input
                type="datetime-local"
                value={customTo}
                onChange={(e) => setCustomTo(e.target.value)}
                className="w-full px-2 py-1.5 text-xs rounded border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </label>
            <button
              onClick={applyCustom}
              className="w-full py-2 rounded bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold transition-colors"
            >
              Apply range
            </button>
          </div>
        </div>,
        document.body,
      )}
    </div>
  )
}
