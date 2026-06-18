import type { EventBus } from './EventBus'
import type { MapModel } from './MapModel'
import type { VehicleState, RaceStatus, RaceResult, GhostFrame } from './types'

export class RaceSession {
  private _status: RaceStatus = 'idle'
  private _elapsedMs = 0
  private _startTimeMs = 0
  private _ghostFrames: GhostFrame[] = []
  private _nextCheckpointOrder = 0
  private _splitTimesMs: number[] = []

  constructor(
    private readonly model: MapModel,
    private readonly bus: EventBus
  ) {}

  get status(): RaceStatus {
    return this._status
  }

  get elapsedMs(): number {
    return this._elapsedMs
  }

  get ghostFrames(): readonly GhostFrame[] {
    return this._ghostFrames
  }

  update(prevState: VehicleState, currState: VehicleState, nowMs: number): void {
    const prev = prevState.position
    const curr = currState.position

    if (this._status === 'idle') {
      if (this.model.isCrossingLine(prev, curr, this.model.manifest.startLine)) {
        this._status = 'racing'
        this._startTimeMs = nowMs
        this._elapsedMs = 0
        this._ghostFrames = []
        this._nextCheckpointOrder = 0
        this._splitTimesMs = []
        this.bus.emit('raceStatusChanged', 'racing')
      }
      return
    }

    if (this._status === 'racing') {
      this._elapsedMs = nowMs - this._startTimeMs

      this._ghostFrames.push({ timeMs: this._elapsedMs, state: currState })
      this.bus.emit('ghostUpdated', { timeMs: this._elapsedMs, state: currState })

      const nextCp = this.model.getCheckpointByOrder(this._nextCheckpointOrder)
      if (nextCp && this.model.isCrossingLine(prev, curr, nextCp)) {
        this._splitTimesMs.push(this._elapsedMs)
        this.bus.emit('checkpointPassed', {
          checkpointId: nextCp.id,
          splitTimeMs: this._elapsedMs,
        })
        this._nextCheckpointOrder++
      }

      const allCheckpointsDone =
        this._nextCheckpointOrder >= this.model.manifest.checkpoints.length
      if (
        allCheckpointsDone &&
        this.model.isCrossingLine(prev, curr, this.model.manifest.finishLine)
      ) {
        this._status = 'finished'
        const result: RaceResult = {
          totalTimeMs: this._elapsedMs,
          splitTimesMs: this._splitTimesMs,
          completedAt: nowMs,
        }
        this.persistBestTime(result.totalTimeMs)
        this.bus.emit('lapCompleted', result)
        this.bus.emit('raceStatusChanged', 'finished')
      }
    }
  }

  reset(): void {
    this._status = 'idle'
    this._elapsedMs = 0
    this._ghostFrames = []
    this._nextCheckpointOrder = 0
    this._splitTimesMs = []
    this.bus.emit('raceStatusChanged', 'idle')
  }

  private persistBestTime(timeMs: number): void {
    const key = `bestTime_${this.model.manifest.name}`
    const existing = localStorage.getItem(key)
    if (existing === null || timeMs < Number(existing)) {
      localStorage.setItem(key, String(timeMs))
    }
  }
}
