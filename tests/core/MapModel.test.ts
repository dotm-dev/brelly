import { describe, it, expect } from 'vitest'
import { MapModel } from '@core/MapModel'
import type { MapPack, Vec3 } from '@core/types'

function makeMapPack(overrides: Partial<MapPack['manifest']> = {}): MapPack {
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
      checkpoints: [
        { id: 'cp0', position: { x: 0, y: 0, z: 50 }, normal: { x: 0, y: 0, z: 1 }, widthMetres: 10, order: 0 },
      ],
      assets: {
        terrain: 'terrain.glb',
        roads: 'roads.glb',
        buildings: 'buildings.glb',
        vegetationData: 'vegetation.json',
      },
      roadGraph: 'road-graph.json',
      bounds: { min: { x: -100, y: -10, z: -100 }, max: { x: 100, y: 50, z: 200 } },
      ...overrides,
    },
  }
}

describe('MapModel', () => {
  it('exposes manifest and roadGraph from the pack', () => {
    const pack = makeMapPack()
    const model = new MapModel(pack)
    expect(model.manifest).toBe(pack.manifest)
    expect(model.roadGraph).toBe(pack.roadGraph)
    expect(model.basePath).toBe('/maps/test')
  })

  it('isCrossingLine returns false when vehicle has not crossed', () => {
    const model = new MapModel(makeMapPack())
    const prev: Vec3 = { x: 0, y: 0, z: -5 }
    const curr: Vec3 = { x: 0, y: 0, z: -2 }
    const line = model.manifest.startLine
    expect(model.isCrossingLine(prev, curr, line)).toBe(false)
  })

  it('isCrossingLine returns true when vehicle crosses from negative to positive side', () => {
    const model = new MapModel(makeMapPack())
    const prev: Vec3 = { x: 0, y: 0, z: -1 }
    const curr: Vec3 = { x: 0, y: 0, z: 1 }
    const line = model.manifest.startLine
    expect(model.isCrossingLine(prev, curr, line)).toBe(true)
  })

  it('isCrossingLine returns false when vehicle crosses in reverse direction', () => {
    const model = new MapModel(makeMapPack())
    const prev: Vec3 = { x: 0, y: 0, z: 1 }
    const curr: Vec3 = { x: 0, y: 0, z: -1 }
    const line = model.manifest.startLine
    expect(model.isCrossingLine(prev, curr, line)).toBe(false)
  })

  it('getCheckpointByOrder returns the correct checkpoint', () => {
    const model = new MapModel(makeMapPack())
    const cp = model.getCheckpointByOrder(0)
    expect(cp?.id).toBe('cp0')
  })

  it('getCheckpointByOrder returns undefined for out-of-range order', () => {
    const model = new MapModel(makeMapPack())
    expect(model.getCheckpointByOrder(99)).toBeUndefined()
  })
})
