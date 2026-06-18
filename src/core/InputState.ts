import type { InputState as IInputState } from './types'

export class InputState implements IInputState {
  throttle = 0
  brake = 0
  steer = 0
  handbrake = false

  reset(): void {
    this.throttle = 0
    this.brake = 0
    this.steer = 0
    this.handbrake = false
  }
}
