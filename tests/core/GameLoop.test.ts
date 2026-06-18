import { describe, it, expect, vi, beforeEach } from 'vitest'
import { GameLoop } from '@core/GameLoop'
import { EventBus } from '@core/EventBus'
import { MapModel } from '@core/MapModel'
import { InputState } from '@core/InputState'
import { VehicleSimulation } from '@core/VehicleSimulation'
import { RaceSession } from '@core/RaceSession'
import type { IPhysicsProvider, MapPack, VehicleState } from '@core/types'

function makeMapPack(): MapPack {
  return {
    basePath: '/maps/test',
    roadGraph: { nodes: [], edges: [] },
    manifest: {
      name: 'test',
      displayName: 'Test Map',
      spawnPosition: { x: 0, y: 0, z: 0 },
      spawnRotation: { x: 0, y: 0, z: 0, w: 1 },
      startLine: { position: { x: 0, y: 0, z: 0 }, normal: { x: 0, y: 0, z: 1 }, widthMetres: 10 },
      finishLine: { position: { x: 0, y: 0, z: 100 }, normal: { x: 0, y: 0, z: 1 }, widthMetres: 10 },
      checkpoints: [],
      assets: {
        terrain: 'terrain.glb',
        roads: 'roads.glb',
        buildings: 'buildings.glb',
        vegetationData: 'vegetation.json',
      },
      roadGraph: 'road-graph.json',
      bounds: { min: { x: -100, y: -10, z: -100 }, max: { x: 100, y: 50, z: 200 } },
    },
  }
}

function makePhysicsProvider(posZ = 0): IPhysicsProvider {
  const state: VehicleState = {
    position: { x: 0, y: 0, z: posZ },
    rotation: { x: 0, y: 0, z: 0, w: 1 },
    velocityKph: 50,
    steeringAngle: 0,
    wheelContacts: [true, true, true, true],
  }
  return {
    applyInput: vi.fn(),
    step: vi.fn(),
    getVehicleState: vi.fn(() => ({ ...state, position: { ...state.position } })),
    dispose: vi.fn(),
  }
}

function makeLocalStorageStub() {
  const store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { Object.keys(store).forEach(k => delete store[k]) },
  }
}

describe('GameLoop', () => {
  let bus: EventBus
  let input: InputState
  let sim: VehicleSimulation
  let session: RaceSession
  let loop: GameLoop

  beforeEach(() => {
    vi.stubGlobal('localStorage', makeLocalStorageStub())
    bus = new EventBus()
    input = new InputState()
    const provider = makePhysicsProvider(2)
    sim = new VehicleSimulation(provider)
    const model = new MapModel(makeMapPack())
    session = new RaceSession(model, bus)
    loop = new GameLoop(sim, session, input, bus)
  })

  it('calls sim.update with current input and dt on each tick', () => {
    const updateSpy = vi.spyOn(sim, 'update')
    input.throttle = 0.5
    loop.tick(0.016, 0)
    expect(updateSpy).toHaveBeenCalledWith(input, 0.016)
  })

  it('emits vehicleUpdated event after each tick', () => {
    const handler = vi.fn()
    bus.on('vehicleUpdated', handler)
    loop.tick(0.016, 0)
    expect(handler).toHaveBeenCalledOnce()
  })

  it('passes vehicle state as vehicleUpdated payload', () => {
    const handler = vi.fn()
    bus.on('vehicleUpdated', handler)
    loop.tick(0.016, 0)
    const payload = handler.mock.calls[0]?.[0] as VehicleState
    expect(payload).toHaveProperty('velocityKph')
    expect(payload).toHaveProperty('position')
  })

  it('calls session.update each tick', () => {
    const sessionSpy = vi.spyOn(session, 'update')
    loop.tick(0.016, 100)
    expect(sessionSpy).toHaveBeenCalledOnce()
  })
})
