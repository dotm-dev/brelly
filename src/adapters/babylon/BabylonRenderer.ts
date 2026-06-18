// src/adapters/babylon/BabylonRenderer.ts
import {
  Engine,
  Scene,
  ArcRotateCamera,
  FollowCamera,
  HemisphericLight,
  DirectionalLight,
  Vector3,
  Quaternion,
  MeshBuilder,
  StandardMaterial,
  Color3,
  SceneLoader,
  AbstractMesh,
  TransformNode,
} from '@babylonjs/core'
import '@babylonjs/loaders/glTF'
import type { IRenderer, MapPack, VehicleState, GhostFrame } from '@core/types'

export class BabylonRenderer implements IRenderer {
  private engine: Engine
  readonly scene: Scene
  private vehicleMesh: TransformNode | null = null
  private ghostMesh: AbstractMesh | null = null
  private resizeHandler: () => void

  constructor(canvas: HTMLCanvasElement) {
    this.engine = new Engine(canvas, true, { adaptToDeviceRatio: true })
    this.scene = new Scene(this.engine)
    this.resizeHandler = () => this.engine.resize()
    window.addEventListener('resize', this.resizeHandler)
    this.setupLights()
    this.setupFallbackGround()
  }

  private setupLights(): void {
    const hemi = new HemisphericLight('hemi', new Vector3(0, 1, 0), this.scene)
    hemi.intensity = 0.7
    const sun = new DirectionalLight('sun', new Vector3(-1, -2, -1), this.scene)
    sun.intensity = 0.8
  }

  private setupFallbackGround(): void {
    const ground = MeshBuilder.CreateGround(
      'fallback-ground',
      { width: 200, height: 200, subdivisions: 4 },
      this.scene
    )
    const mat = new StandardMaterial('fallback-mat', this.scene)
    mat.diffuseColor = new Color3(0.25, 0.4, 0.25)
    ground.material = mat
  }

  private setupFollowCamera(target: TransformNode): void {
    this.scene.cameras.slice().forEach(c => c.dispose())

    const cam = new FollowCamera('follow-cam', new Vector3(0, 5, -10), this.scene)
    cam.lockedTarget = target as unknown as AbstractMesh
    cam.radius = 12
    cam.heightOffset = 4
    cam.rotationOffset = 0
    cam.cameraAcceleration = 0.05
    cam.maxCameraSpeed = 20
    this.scene.activeCamera = cam
  }

  // Available for use when no vehicle is spawned
  private _setupOrbitCamera(): void {
    const cam = new ArcRotateCamera('orbit', -Math.PI / 2, Math.PI / 3, 20, Vector3.Zero(), this.scene)
    cam.lowerRadiusLimit = 5
    cam.upperRadiusLimit = 100
    this.scene.activeCamera = cam
  }

  async loadMap(pack: MapPack): Promise<void> {
    this.scene.getMeshByName('fallback-ground')?.dispose()

    const load = (path: string) =>
      SceneLoader.ImportMeshAsync('', pack.basePath + '/', path, this.scene)

    await Promise.all([
      load(pack.manifest.assets.terrain),
      load(pack.manifest.assets.roads),
      load(pack.manifest.assets.buildings),
    ])
  }

  spawnVehicleMesh(): TransformNode {
    const root = new TransformNode('vehicle-root', this.scene)
    const body = MeshBuilder.CreateBox('vehicle-body', { width: 1.8, height: 0.6, depth: 4 }, this.scene)
    body.position.y = 0.3
    body.parent = root
    const mat = new StandardMaterial('vehicle-mat', this.scene)
    mat.diffuseColor = new Color3(0.9, 0.2, 0.1)
    body.material = mat
    this.vehicleMesh = root
    this.setupFollowCamera(root)
    return root
  }

  updateVehicle(state: VehicleState): void {
    if (!this.vehicleMesh) return
    const { position: p, rotation: r } = state
    this.vehicleMesh.position.set(p.x, p.y, p.z)
    this.vehicleMesh.rotationQuaternion = new Quaternion(r.x, r.y, r.z, r.w)
  }

  updateGhost(frame: GhostFrame | null): void {
    if (!frame) {
      this.ghostMesh?.setEnabled(false)
      return
    }
    if (!this.ghostMesh) {
      this.ghostMesh = MeshBuilder.CreateBox('ghost-body', { width: 1.8, height: 0.6, depth: 4 }, this.scene)
      const mat = new StandardMaterial('ghost-mat', this.scene)
      mat.diffuseColor = new Color3(0.4, 0.6, 1.0)
      mat.alpha = 0.4
      this.ghostMesh.material = mat
    }
    this.ghostMesh.setEnabled(true)
    const { position: p, rotation: r } = frame.state
    this.ghostMesh.position.set(p.x, p.y, p.z)
    this.ghostMesh.rotationQuaternion = new Quaternion(r.x, r.y, r.z, r.w)
  }

  startRenderLoop(onBeforeRender: () => void): void {
    this.engine.runRenderLoop(() => {
      onBeforeRender()
      this.scene.render()
    })
  }

  dispose(): void {
    window.removeEventListener('resize', this.resizeHandler)
    this.engine.dispose()
  }
}
