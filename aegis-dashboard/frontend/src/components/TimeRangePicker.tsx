'use client'

import { useState, useEffect, useCallback } from 'react'

export interface TimeRange {
  start: string
  end: string
  interval: string
  label: string
}

const PRESETS: { label: string; minutes: number; interval: string }[] = [
  { label: '15m', minutes: 15, interval: '1m' },
  { label: '1h', minutes: 60, interval: '1m' },
  { label: '4h', minutes: 240, interval: '5m' },
  { label: '1d', minutes: 1440, interval: '15m' },
  { label: '7d', minutes: 10080, interval: '1h' },
]

interface TimeRangePickerProps {
  value: TimeRange
  onChange: (range: TimeRange) => void
}

function buildRange(minutes: number, interval: string, label: string): TimeRange {
  const end = new Date()
  const start = new Date(end.getTime() - minutes * 60 * 1000)
  return {
    start: start.toISOString(),
    end: end.toISOString(),
    interval,
    label,
  }
}

export function useTimeRange(defaultLabel = '1h') {
  const preset = PRESETS.find((p) => p.label === defaultLabel) || PRESETS[1]
  const [range, setRange] = useState<TimeRange>(() =>
    buildRange(preset.minutes, preset.interval, preset.label)
  )
  const [autoRefresh, setAutoRefresh] = useState(false)

  const selectPreset = useCallback((label: string) => {
    const p = PRESETS.find((pr) => pr.label === label) || PRESETS[1]
    setRange(buildRange(p.minutes, p.interval, p.label))
  }, [])

  const refresh = useCallback(() => {
    const p = PRESETS.find((pr) => pr.label === range.label) || PRESETS[1]
    setRange(buildRange(p.minutes, p.interval, p.label))
  }, [range.label])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(refresh, 30_000)
    return () => clearInterval(id)
  }, [autoRefresh, refresh])

  return { range, selectPreset, autoRefresh, setAutoRefresh, refresh }
}

export function TimeRangePicker({ value, onChange }: TimeRangePickerProps) {
  const [autoRefresh, setAutoRefresh] = useState(false)

  const handlePreset = (p: (typeof PRESETS)[number]) => {
    onChange(buildRange(p.minutes, p.interval, p.label))
  }

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(() => {
      const p = PRESETS.find((pr) => pr.label === value.label) || PRESETS[1]
      onChange(buildRange(p.minutes, p.interval, p.label))
    }, 30_000)
    return () => clearInterval(id)
  }, [autoRefresh, value.label, onChange])

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-sm font-medium text-muted-foreground">Time range:</span>
      <div className="flex items-center gap-1">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => handlePreset(p)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              value.label === p.label
                ? 'bg-primary text-primary-foreground'
                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="ml-2 flex items-center gap-1.5">
        <button
          onClick={() => {
            const preset = PRESETS.find((pr) => pr.label === value.label) || PRESETS[1]
            onChange(buildRange(preset.minutes, preset.interval, preset.label))
          }}
          className="px-2 py-1.5 rounded-md text-sm bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
          title="Refresh now"
        >
          ↻
        </button>
        <label className="flex items-center gap-1 text-sm text-muted-foreground cursor-pointer">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="rounded"
          />
          Auto
        </label>
      </div>
    </div>
  )
}
