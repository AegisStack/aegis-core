/**
 * Tests for TimeRangePicker.
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TimeRangePicker, buildRange, PRESETS, type TimeRange } from '../TimeRangePicker'

describe('buildRange', () => {
  it('builds a range ending now, starting `minutes` earlier', () => {
    const range = buildRange(60, '1m', '1h')
    const diffMs = new Date(range.end).getTime() - new Date(range.start).getTime()
    expect(diffMs).toBe(60 * 60 * 1000)
    expect(range.interval).toBe('1m')
    expect(range.label).toBe('1h')
  })
})

describe('TimeRangePicker', () => {
  function renderPicker(value: TimeRange, onChange = jest.fn()) {
    render(<TimeRangePicker value={value} onChange={onChange} />)
    return onChange
  }

  it('shows the preset display label for the current value', () => {
    renderPicker(buildRange(60, '1m', '1h'))
    expect(screen.getByText('Past hour')).toBeInTheDocument()
  })

  it('opens the dropdown with all presets when the trigger is clicked', async () => {
    const user = userEvent.setup()
    renderPicker(buildRange(60, '1m', '1h'))

    await user.click(screen.getByText('Past hour'))

    for (const preset of PRESETS) {
      // "Past hour" appears twice once open: once as the trigger's current
      // value, once as a dropdown option.
      expect(screen.getAllByText(preset.display).length).toBeGreaterThan(0)
    }
  })

  it('calls onChange with a new range when a preset is selected', async () => {
    const user = userEvent.setup()
    const onChange = renderPicker(buildRange(60, '1m', '1h'))

    await user.click(screen.getByText('Past hour'))
    await user.click(screen.getByText('Past day'))

    expect(onChange).toHaveBeenCalledTimes(1)
    const range = onChange.mock.calls[0][0] as TimeRange
    expect(range.label).toBe('1d')
    expect(range.interval).toBe('15m')
  })

  it('calls onChange with a fresh range of the same preset on refresh', async () => {
    const user = userEvent.setup()
    const onChange = renderPicker(buildRange(60, '1m', '1h'))

    await user.click(screen.getByTitle('Refresh now'))

    expect(onChange).toHaveBeenCalledTimes(1)
    expect((onChange.mock.calls[0][0] as TimeRange).label).toBe('1h')
  })

  it('toggles the Live button state on click', async () => {
    const user = userEvent.setup()
    renderPicker(buildRange(60, '1m', '1h'))

    const liveButton = screen.getByTitle('Enable live updates (30s)')
    await user.click(liveButton)

    expect(screen.getByTitle('Stop live updates')).toBeInTheDocument()
  })

  it('shows a formatted from/to label for a custom range', () => {
    renderPicker({
      start: '2024-01-15T10:00:00Z',
      end: '2024-01-15T11:00:00Z',
      interval: '1m',
      label: 'custom',
    })
    expect(screen.getByText(/→/)).toBeInTheDocument()
  })
})
