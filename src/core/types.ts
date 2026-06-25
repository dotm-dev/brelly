// ─── Primitives ───────────────────────────────────────────────────────────────

export interface Vec3 {
  x: number
  y: number
  z: number
}

export interface Quat {
  x: number
  y: number
  z: number
  w: number
}

// ─── Vehicle ──────────────────────────────────────────────────────────────────

export interface VehicleState {
  position: Vec3
  rotation: Quat
  velocityKph: number
  steeringAngle: number       // radians, positive = right
  wheelContacts: [boolean, boolean, boolean, boolean] // FL, FR, RL, RR
}

export interface VehicleConfig {
  mass: number                // kg
  engineForce: number         // max force in newtons
  brakeForce: number          // max brake force in newtons
  maxSteeringAngle: number    // radians
  wheelBase: number           // metres, front-to-rear axle distance
  trackWidth: number          // metres, left-to-right wheel distance
  suspensionRestLength: number
  suspensionStiffness: number
  suspensionDamping: number
  meshPath: string            // path to vehicle .glb relative to map root
}

// ─── Input ────────────────────────────────────────────────────────────────────

export interface InputState {
  throttle: number    // 0–1
  brake: number       // 0–1
  steer: number       // -1 (full left) to 1 (full right)
  handbrake: boolean
}

// ─── Map ──────────────────────────────────────────────────────────────────────

export interface RoadNode {
  id: string
  position: Vec3
}

export interface RoadEdge {
  id: string
  fromNodeId: string
  toNodeId: string
  widthMetres: number
}

export interface RoadGraph {
  nodes: RoadNode[]
  edges: RoadEdge[]
}

export interface CheckpointDefinition {
  id: string
  position: Vec3
  normal: Vec3          // direction vehicle must cross from
  widthMetres: number
  order: number         // 0-indexed, must be crossed in order
}

export interface MapManifest {
  name: string
  displayName: string
  spawnPosition: Vec3
  spawnRotation: Quat
  startLine: { position: Vec3; normal: Vec3; widthMetres: number }
  finishLine: { position: Vec3; normal: Vec3; widthMetres: number }
  checkpoints: CheckpointDefinition[]
  assets: {
    terrain: string        // relative path to terrain.glb
    terrainTexture?: string // relative path to satellite texture (separate from GLB)
    terrainLod1?: string   // relative path to terrain_lod1.glb (optional, for LOD)
    terrainLod2?: string   // relative path to terrain_lod2.glb (optional, for LOD)
    roads: string          // relative path to roads.glb
    buildings: string      // relative path to buildings.glb
    vegetation?: string    // relative path to vegetation.glb
    vegetationData: string // relative path to vegetation.json
  }
  roadGraph: string     // relative path to road-graph.json
  bounds: { min: Vec3; max: Vec3 }
}

export interface MapPack {
  manifest: MapManifest
  roadGraph: RoadGraph
  basePath: string      // URL prefix for loading .glb assets
}

// ─── Race ─────────────────────────────────────────────────────────────────────

export type RaceStatus = 'idle' | 'countdown' | 'racing' | 'finished'

export interface RaceResult {
  totalTimeMs: number
  splitTimesMs: number[]    // one per checkpoint
  completedAt: number       // Date.now() timestamp
}

export interface GhostFrame {
  timeMs: number
  state: VehicleState
}

// ─── Events ───────────────────────────────────────────────────────────────────

export interface EventMap {
  vehicleUpdated: VehicleState
  raceStatusChanged: RaceStatus
  checkpointPassed: { checkpointId: string; splitTimeMs: number }
  lapCompleted: RaceResult
  ghostUpdated: GhostFrame | null
  countdownTick: number     // 3, 2, 1, 0 (go)
}

// ─── Adapter interfaces ───────────────────────────────────────────────────────

export interface IPhysicsProvider {
  applyInput(input: InputState): void
  getVehicleState(): VehicleState
  step(dt: number): void
  dispose(): void
}

export interface IRenderer {
  loadMap(pack: MapPack): Promise<void>
  updateVehicle(state: VehicleState): void
  updateGhost(state: GhostFrame | null): void
  dispose(): void
}
