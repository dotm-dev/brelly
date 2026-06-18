// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { InputHandler } from '@adapters/babylon/InputHandler'
import { InputState } from '@core/InputState'

function fireKey(type: 'keydown' | 'keyup', code: string): void {
  window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }))
}

describe('InputHandler', () => {
  let handler: InputHandler
  let state: InputState

  beforeEach(() => {
    state = new InputState()
    handler = new InputHandler(state)
  })

  afterEach(() => {
    handler.dispose()
  })

  it('sets throttle to 1 when ArrowUp is pressed', () => {
    fireKey('keydown', 'ArrowUp')
    handler.update()
    expect(state.throttle).toBe(1)
  })

  it('resets throttle to 0 when ArrowUp is released', () => {
    fireKey('keydown', 'ArrowUp')
    handler.update()
    fireKey('keyup', 'ArrowUp')
    handler.update()
    expect(state.throttle).toBe(0)
  })

  it('sets brake to 1 when ArrowDown is pressed', () => {
    fireKey('keydown', 'ArrowDown')
    handler.update()
    expect(state.brake).toBe(1)
  })

  it('sets steer to -1 when ArrowLeft is pressed', () => {
    fireKey('keydown', 'ArrowLeft')
    handler.update()
    expect(state.steer).toBe(-1)
  })

  it('sets steer to 1 when ArrowRight is pressed', () => {
    fireKey('keydown', 'ArrowRight')
    handler.update()
    expect(state.steer).toBe(1)
  })

  it('sets handbrake to true when Space is pressed', () => {
    fireKey('keydown', 'Space')
    handler.update()
    expect(state.handbrake).toBe(true)
  })

  it('resets steer to 0 when no steering key is held', () => {
    fireKey('keydown', 'ArrowLeft')
    handler.update()
    fireKey('keyup', 'ArrowLeft')
    handler.update()
    expect(state.steer).toBe(0)
  })

  it('removes event listeners on dispose', () => {
    handler.dispose()
    fireKey('keydown', 'ArrowUp')
    handler.update()
    expect(state.throttle).toBe(0)
  })

  it('sets throttle to 1 when KeyW is pressed', () => {
    fireKey('keydown', 'KeyW')
    handler.update()
    expect(state.throttle).toBe(1)
  })

  it('sets steer to -1 when KeyA is pressed', () => {
    fireKey('keydown', 'KeyA')
    handler.update()
    expect(state.steer).toBe(-1)
  })
})
