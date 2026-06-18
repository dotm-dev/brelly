import type { VehicleState } from './types'
import type { EventBus } from './EventBus'
import type { InputState } from './InputState'
import type { VehicleSimulation } from './VehicleSimulation'
import type { RaceSession } from './RaceSession'

export class GameLoop {
  private prevState: VehicleState

  constructor(
    private readonly sim: VehicleSimulation,
    private readonly session: RaceSession,
    private readonly input: InputState,
    private readonly bus: EventBus
  ) {
    this.prevState = this.sim.state
  }

  /**
   * Advance one frame.
   * @param dt  Delta time in seconds
   * @param nowMs  Monotonic clock in milliseconds (e.g. performance.now())
   */
  tick(dt: number, nowMs: number): void {
    const prev = this.prevState
    this.sim.update(this.input, dt)
    const curr = this.sim.state
    this.session.update(prev, curr, nowMs)
    this.bus.emit('vehicleUpdated', curr)
    this.prevState = curr
  }
}
