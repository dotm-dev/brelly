import type { InputState } from '@core/InputState'

export class InputHandler {
  private held = new Set<string>()
  private onKeyDown: (e: KeyboardEvent) => void
  private onKeyUp: (e: KeyboardEvent) => void

  constructor(private readonly state: InputState) {
    this.onKeyDown = (e) => this.held.add(e.code)
    this.onKeyUp = (e) => this.held.delete(e.code)
    window.addEventListener('keydown', this.onKeyDown)
    window.addEventListener('keyup', this.onKeyUp)
  }

  /** Call once per frame before GameLoop.tick() to flush key state into InputState. */
  update(): void {
    this.state.throttle = this.held.has('ArrowUp') || this.held.has('KeyW') ? 1 : 0
    this.state.brake = this.held.has('ArrowDown') || this.held.has('KeyS') ? 1 : 0
    this.state.steer =
      (this.held.has('ArrowRight') || this.held.has('KeyD') ? 1 : 0) -
      (this.held.has('ArrowLeft') || this.held.has('KeyA') ? 1 : 0)
    this.state.handbrake = this.held.has('Space')

    // Gamepad (first connected gamepad wins)
    const gp = navigator.getGamepads?.()[0]
    if (gp) {
      const steerAxis = gp.axes[0] ?? 0
      const throttleBtn = gp.buttons[7]?.value ?? 0
      const brakeBtn = gp.buttons[6]?.value ?? 0
      const handbrakeBtn = gp.buttons[0]?.pressed ?? false

      if (Math.abs(steerAxis) > 0.05) this.state.steer = steerAxis
      if (throttleBtn > 0.05) this.state.throttle = throttleBtn
      if (brakeBtn > 0.05) this.state.brake = brakeBtn
      if (handbrakeBtn) this.state.handbrake = true
    }
  }

  dispose(): void {
    window.removeEventListener('keydown', this.onKeyDown)
    window.removeEventListener('keyup', this.onKeyUp)
  }
}
