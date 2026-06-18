import { describe, it, expect, vi } from 'vitest'
import { VehicleSimulation } from '@core/VehicleSimulation'
import { InputState } from '@core/InputState'
import type { IPhysicsProvider, VehicleState } from '@core/types'

function makeVehicleState(overrides: Partial<VehicleState> = {}): VehicleState {
  return {
    position: { x: 0, y: 0, z: 0 },
    rotation: { x: 0, y: 0, z: 0, w: 1 },
    velocityKph: 0,
    steeringAngle: 0,
    wheelContacts: [true, true, true, true],
    ...overrides,
  }
}

function makePhysicsProvider(stateOverrides: Partial<VehicleState> = {}): IPhysicsProvider {
  return {
    applyInput: vi.fn(),
    getVehicleState: vi.fn(() => makeVehicleState(stateOverrides)),
    step: vi.fn(),
    dispose: vi.fn(),
  }
}

describe('VehicleSimulation', () => {
  it('calls applyInput and step on the physics provider each update', () => {
    const provider = makePhysicsProvider()
    const input = new InputState()
    const sim = new VehicleSimulation(provider)
    input.throttle = 0.8
    sim.update(input, 0.016)
    expect(provider.applyInput).toHaveBeenCalledWith(input)
    expect(provider.step).toHaveBeenCalledWith(0.016)
  })

  it('returns vehicle state from the physics provider', () => {
    const provider = makePhysicsProvider({ velocityKph: 60 })
    const sim = new VehicleSimulation(provider)
    sim.update(new InputState(), 0.016)
    expect(sim.state.velocityKph).toBe(60)
  })

  it('exposes the latest state after multiple updates', () => {
    let callCount = 0
    const provider: IPhysicsProvider = {
      applyInput: vi.fn(),
      step: vi.fn(),
      dispose: vi.fn(),
      getVehicleState: vi.fn(() => makeVehicleState({ velocityKph: callCount++ * 10 })),
    }
    const sim = new VehicleSimulation(provider)
    sim.update(new InputState(), 0.016)
    sim.update(new InputState(), 0.016)
    expect(sim.state.velocityKph).toBe(10)
  })

  it('calls dispose on the provider when disposed', () => {
    const provider = makePhysicsProvider()
    const sim = new VehicleSimulation(provider)
    sim.dispose()
    expect(provider.dispose).toHaveBeenCalledOnce()
  })
})
