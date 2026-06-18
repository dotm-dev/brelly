import { describe, it, expect, vi, beforeEach } from 'vitest'
import { RaceSession } from '@core/RaceSession'
import { EventBus } from '@core/EventBus'
import { MapModel } from '@core/MapModel'
import type { MapPack, VehicleState } from '@core/types'

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

function makeState(z: number): VehicleState {
  return {
    position: { x: 0, y: 0, z },
    rotation: { x: 0, y: 0, z: 0, w: 1 },
    velocityKph: 50,
    steeringAngle: 0,
    wheelContacts: [true, true, true, true],
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

describe('RaceSession', () => {
  let bus: EventBus
  let model: MapModel
  let session: RaceSession

  beforeEach(() => {
    vi.stubGlobal('localStorage', makeLocalStorageStub())
    bus = new EventBus()
    model = new MapModel(makeMapPack())
    session = new RaceSession(model, bus)
  })

  it('starts in idle state', () => {
    expect(session.status).toBe('idle')
  })

  it('transitions to racing when start line is crossed while idle', () => {
    session.update(makeState(-1), makeState(1), 0)
    expect(session.status).toBe('racing')
  })

  it('emits raceStatusChanged event when transitioning to racing', () => {
    const handler = vi.fn()
    bus.on('raceStatusChanged', handler)
    session.update(makeState(-1), makeState(1), 0)
    expect(handler).toHaveBeenCalledWith('racing')
  })

  it('tracks elapsed time while racing', () => {
    session.update(makeState(-1), makeState(1), 0)
    session.update(makeState(1), makeState(2), 1000)
    expect(session.elapsedMs).toBeGreaterThan(0)
  })

  it('transitions to finished when finish line is crossed while racing', () => {
    session.update(makeState(-1), makeState(1), 0)
    session.update(makeState(99), makeState(101), 2000)
    expect(session.status).toBe('finished')
  })

  it('emits lapCompleted event with totalTimeMs when finishing', () => {
    const handler = vi.fn()
    bus.on('lapCompleted', handler)
    session.update(makeState(-1), makeState(1), 0)
    session.update(makeState(99), makeState(101), 3000)
    expect(handler).toHaveBeenCalledOnce()
    const result = handler.mock.calls[0]?.[0]
    expect(result.totalTimeMs).toBeGreaterThan(0)
  })

  it('records ghost frames while racing and clears on reset', () => {
    session.update(makeState(-1), makeState(1), 0)
    session.update(makeState(1), makeState(2), 16)
    expect(session.ghostFrames.length).toBeGreaterThan(0)
    session.reset()
    expect(session.status).toBe('idle')
    expect(session.ghostFrames.length).toBe(0)
  })

  it('persists best time to localStorage on finish', () => {
    session.update(makeState(-1), makeState(1), 0)
    session.update(makeState(99), makeState(101), 5000)
    const stored = localStorage.getItem('bestTime_test')
    expect(stored).not.toBeNull()
    expect(Number(stored)).toBeGreaterThan(0)
  })
})
