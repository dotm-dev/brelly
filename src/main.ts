import { BabylonScene } from '@adapters/babylon/BabylonScene'

const canvas = document.getElementById('render-canvas') as HTMLCanvasElement
if (!canvas) throw new Error('Canvas element #render-canvas not found')

const scene = new BabylonScene(canvas)
scene.start()
