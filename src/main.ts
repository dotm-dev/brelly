// src/main.ts
import { GameApp } from '@adapters/babylon/GameApp'

const canvas = document.getElementById('render-canvas') as HTMLCanvasElement
if (!canvas) throw new Error('Canvas element #render-canvas not found')

const app = new GameApp(canvas)
app.start().catch(console.error)
