import type { MapPack, MapManifest, RoadGraph, Vec3, CheckpointDefinition } from './types'

type LineDefinition = { position: Vec3; normal: Vec3; widthMetres: number }

export class MapModel {
  readonly manifest: MapManifest
  readonly roadGraph: RoadGraph
  readonly basePath: string

  constructor(pack: MapPack) {
    this.manifest = pack.manifest
    this.roadGraph = pack.roadGraph
    this.basePath = pack.basePath
  }

  /**
   * Returns true when the vehicle transitions from the negative side of a line
   * to the positive side (i.e. crosses in the direction of the line's normal).
   */
  isCrossingLine(prevPos: Vec3, currPos: Vec3, line: LineDefinition): boolean {
    const prevDist = this.signedDist(prevPos, line)
    const currDist = this.signedDist(currPos, line)
    return prevDist < 0 && currDist >= 0
  }

  getCheckpointByOrder(order: number): CheckpointDefinition | undefined {
    return this.manifest.checkpoints.find(cp => cp.order === order)
  }

  private signedDist(pos: Vec3, line: LineDefinition): number {
    const dx = pos.x - line.position.x
    const dy = pos.y - line.position.y
    const dz = pos.z - line.position.z
    return dx * line.normal.x + dy * line.normal.y + dz * line.normal.z
  }
}
