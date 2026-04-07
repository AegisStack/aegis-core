/**
 * Tests for utility functions.
 */

import { formatRelativeTime, formatDate } from '../utils'

describe('formatRelativeTime', () => {
  it('formats recent time as "just now"', () => {
    const now = new Date()
    expect(formatRelativeTime(now)).toBe('just now')
  })

  it('formats minutes ago', () => {
    const date = new Date(Date.now() - 5 * 60 * 1000) // 5 minutes ago
    expect(formatRelativeTime(date)).toBe('5m ago')
  })

  it('formats hours ago', () => {
    const date = new Date(Date.now() - 3 * 60 * 60 * 1000) // 3 hours ago
    expect(formatRelativeTime(date)).toBe('3h ago')
  })

  it('formats days ago', () => {
    const date = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000) // 2 days ago
    expect(formatRelativeTime(date)).toBe('2d ago')
  })

  it('handles ISO string input', () => {
    const date = new Date(Date.now() - 30 * 60 * 1000) // 30 minutes ago
    expect(formatRelativeTime(date.toISOString())).toBe('30m ago')
  })
})

describe('formatDate', () => {
  it('formats date to locale string', () => {
    const date = new Date('2024-01-15T14:30:00Z')
    const formatted = formatDate(date)
    // Just check it returns a string (locale-dependent)
    expect(typeof formatted).toBe('string')
    expect(formatted.length).toBeGreaterThan(0)
  })

  it('handles ISO string input', () => {
    const formatted = formatDate('2024-01-15T14:30:00Z')
    expect(typeof formatted).toBe('string')
    expect(formatted.length).toBeGreaterThan(0)
  })
})
