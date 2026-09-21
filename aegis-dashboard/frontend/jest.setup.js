import '@testing-library/jest-dom'

// jsdom has no layout engine and no ResizeObserver - recharts'
// ResponsiveContainer (used throughout the dashboard charts) needs one to
// mount at all. This no-op stub is enough for it to render without
// crashing; it never fires a real resize callback, so charts render at
// their fallback/zero size under test rather than a real pixel size.
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
