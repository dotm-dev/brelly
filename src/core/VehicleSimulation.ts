import type { IPhysicsProvider, InputState, VehicleState } from './types'

export class VehicleSimulation {
  private provider: IPhysicsProvider
  private _state: VehicleState = {
    position: { x: 0, y: 0, z: 0 },
    rotation: { x: 0, y: 0, z: 0, w: 1 },
    velocityKph: 0,
    steeringAngle: 0,
    wheelContacts: [false, false, false, false],
  }

  constructor(provider: IPhysicsProvider) {
    this.provider = provider
  }

  update(input: InputState, dt: number): void {
    this.provider.applyInput(input)
    this.provider.step(dt)
    this._state = this.provider.getVehicleState()
  }

  get state(): VehicleState {
    return this._state
  }

  dispose(): void {
    this.provider.dispose()
  }
}
