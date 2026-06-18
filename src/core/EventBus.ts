import type { EventMap } from './types'

type Handler<T> = (payload: T) => void

export class EventBus {
  private listeners = new Map<keyof EventMap, Set<Handler<unknown>>>()

  on<K extends keyof EventMap>(event: K, handler: Handler<EventMap[K]>): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(handler as Handler<unknown>)
  }

  off<K extends keyof EventMap>(event: K, handler: Handler<EventMap[K]>): void {
    this.listeners.get(event)?.delete(handler as Handler<unknown>)
  }

  once<K extends keyof EventMap>(event: K, handler: Handler<EventMap[K]>): void {
    const wrapper = (payload: EventMap[K]) => {
      handler(payload)
      this.off(event, wrapper)
    }
    this.on(event, wrapper)
  }

  emit<K extends keyof EventMap>(event: K, payload: EventMap[K]): void {
    this.listeners.get(event)?.forEach(handler => handler(payload as unknown))
  }

  dispose(): void {
    this.listeners.clear()
  }
}
