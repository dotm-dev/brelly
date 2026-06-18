import {
  Engine,
  Scene,
  ArcRotateCamera,
  HemisphericLight,
  MeshBuilder,
  Vector3,
  StandardMaterial,
  Color3,
} from '@babylonjs/core'

export class BabylonScene {
  private engine: Engine
  private scene: Scene

  constructor(canvas: HTMLCanvasElement) {
    this.engine = new Engine(canvas, true, { adaptToDeviceRatio: true })
    this.scene = new Scene(this.engine)
    this.setupCamera(canvas)
    this.setupLight()
    this.setupGround()
    this.setupResizeHandler()
  }

  private setupCamera(canvas: HTMLCanvasElement): void {
    const camera = new ArcRotateCamera(
      'camera',
      -Math.PI / 2,
      Math.PI / 3,
      20,
      Vector3.Zero(),
      this.scene
    )
    camera.attachControl(canvas, true)
    camera.lowerRadiusLimit = 5
    camera.upperRadiusLimit = 100
  }

  private setupLight(): void {
    const light = new HemisphericLight('light', new Vector3(0, 1, 0), this.scene)
    light.intensity = 0.9
  }

  private setupGround(): void {
    const ground = MeshBuilder.CreateGround(
      'ground',
      { width: 50, height: 50, subdivisions: 4 },
      this.scene
    )
    const mat = new StandardMaterial('ground-mat', this.scene)
    mat.diffuseColor = new Color3(0.3, 0.5, 0.3)
    ground.material = mat

    // Placeholder box representing vehicle spawn point
    const box = MeshBuilder.CreateBox('vehicle-placeholder', { size: 1.5 }, this.scene)
    box.position.y = 0.75
    const boxMat = new StandardMaterial('box-mat', this.scene)
    boxMat.diffuseColor = new Color3(0.8, 0.2, 0.2)
    box.material = boxMat
  }

  private setupResizeHandler(): void {
    window.addEventListener('resize', () => this.engine.resize())
  }

  start(): void {
    this.engine.runRenderLoop(() => this.scene.render())
  }

  dispose(): void {
    this.engine.dispose()
  }
}
