import type { EventBus } from '@core/EventBus'
import type { VehicleState, RaceStatus } from '@core/types'

export class HUD {
  private root: HTMLDivElement
  private timerEl: HTMLDivElement
  private speedEl: HTMLDivElement
  private statusEl: HTMLDivElement

  constructor(private readonly bus: EventBus) {
    this.root = document.createElement('div')
    Object.assign(this.root.style, {
      position: 'fixed',
      top: '20px',
      left: '20px',
      color: '#fff',
      fontFamily: 'monospace',
      fontSize: '18px',
      textShadow: '1px 1px 3px #000',
      pointerEvents: 'none',
      userSelect: 'none',
    })

    this.timerEl = this.makeEl('00:00.000')
    this.speedEl = this.makeEl('0 km/h')
    this.statusEl = this.makeEl('READY')

    this.root.append(this.statusEl, this.timerEl, this.speedEl)
    document.body.appendChild(this.root)

    this.bus.on('vehicleUpdated', (state: VehicleState) => {
      this.speedEl.textContent = `${Math.round(state.velocityKph)} km/h`
    })

    this.bus.on('raceStatusChanged', (status: RaceStatus) => {
      const labels: Record<RaceStatus, string> = {
        idle: 'READY',
        countdown: 'GET SET...',
        racing: 'RACING',
        finished: 'FINISHED',
      }
      this.statusEl.textContent = labels[status]
    })

    this.bus.on('lapCompleted', (result) => {
      this.timerEl.textContent = this.formatTime(result.totalTimeMs)
    })
  }

  /** Call each frame while racing to keep the live timer updated. */
  updateTimer(elapsedMs: number): void {
    this.timerEl.textContent = this.formatTime(elapsedMs)
  }

  private formatTime(ms: number): string {
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.floor((ms % 60000) / 1000)
    const millis = ms % 1000
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(millis).padStart(3, '0')}`
  }

  private makeEl(text: string): HTMLDivElement {
    const el = document.createElement('div')
    el.textContent = text
    el.style.margin = '4px 0'
    return el
  }

  dispose(): void {
    this.root.remove()
  }
}
