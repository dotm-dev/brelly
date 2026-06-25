// src/main.ts
import { GameApp } from '@adapters/babylon/GameApp'

const canvas = document.getElementById('render-canvas') as HTMLCanvasElement
if (!canvas) throw new Error('Canvas element #render-canvas not found')

const app = new GameApp(canvas)

const mapName = new URLSearchParams(location.search).get('map')
if (mapName) {
  const base = `maps/${mapName}`
  Promise.all([
    fetch(`${base}/manifest.json`).then(r => r.json()),
    fetch(`${base}/road-graph.json`).then(r => r.json()),
  ]).then(([manifest, roadGraph]) => {
    app.startPreview({ basePath: base, manifest, roadGraph }).catch(console.error)
  }).catch(err => {
    console.error('Failed to load map:', err)
  })
} else {
  app.start().catch(console.error)
}
