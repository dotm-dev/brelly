import { describe, it, expect, vi } from 'vitest'
import { EventBus } from '@core/EventBus'
import type { EventMap } from '@core/types'

describe('EventBus', () => {
  it('calls subscriber when event is emitted', () => {
    const bus = new EventBus()
    const handler = vi.fn()
    bus.on('countdownTick', handler)
    bus.emit('countdownTick', 3)
    expect(handler).toHaveBeenCalledOnce()
    expect(handler).toHaveBeenCalledWith(3)
  })

  it('calls multiple subscribers for the same event', () => {
    const bus = new EventBus()
    const h1 = vi.fn()
    const h2 = vi.fn()
    bus.on('countdownTick', h1)
    bus.on('countdownTick', h2)
    bus.emit('countdownTick', 1)
    expect(h1).toHaveBeenCalledOnce()
    expect(h2).toHaveBeenCalledOnce()
  })

  it('does not call handler after off() is called', () => {
    const bus = new EventBus()
    const handler = vi.fn()
    bus.on('countdownTick', handler)
    bus.off('countdownTick', handler)
    bus.emit('countdownTick', 2)
    expect(handler).not.toHaveBeenCalled()
  })

  it('does not call handlers for different events', () => {
    const bus = new EventBus()
    const handler = vi.fn()
    bus.on('countdownTick', handler)
    bus.emit('raceStatusChanged', 'racing')
    expect(handler).not.toHaveBeenCalled()
  })

  it('once() fires exactly one time', () => {
    const bus = new EventBus()
    const handler = vi.fn()
    bus.once('countdownTick', handler)
    bus.emit('countdownTick', 3)
    bus.emit('countdownTick', 2)
    expect(handler).toHaveBeenCalledOnce()
  })
})
