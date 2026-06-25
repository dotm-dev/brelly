// src/adapters/babylon/BabylonRenderer.ts
import {
  Engine,
  Scene,
  UniversalCamera,
  FollowCamera,
  HemisphericLight,
  DirectionalLight,
  Vector3,
  Quaternion,
  MeshBuilder,
  StandardMaterial,
  Color3,
  Texture,
  SceneLoader,
  AbstractMesh,
  Mesh,
  TransformNode,
} from '@babylonjs/core'
import { GLTFFileLoader } from '@babylonjs/loaders/glTF'
SceneLoader.RegisterPlugin(new GLTFFileLoader())
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
    this.setupPreviewCamera()
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

  private setupPreviewCamera(): void {
    const cam = new UniversalCamera('preview-cam', new Vector3(0, 600, -800), this.scene)
    cam.setTarget(Vector3.Zero())
    cam.speed = 20
    cam.minZ = 1
    // WASD + Q/E for vertical — keyboard input only, mouse handled manually below
    cam.keysUp    = [87] // W
    cam.keysDown  = [83] // S
    cam.keysLeft  = [65] // A
    cam.keysRight = [68] // D
    cam.keysUpward   = [69] // E
    cam.keysDownward = [81] // Q
    this.scene.activeCamera = cam
  }

  attachPreviewControls(canvas: HTMLCanvasElement): void {
    const cam = this.scene.getCameraByName('preview-cam') as UniversalCamera
    // attach keyboard only — remove built-in mouse input to avoid the accumulation bug
    cam.inputs.removeByType('FreeCameraMouseInput')
    cam.inputs.removeByType('FreeCameraMouseWheelInput')
    cam.attachControl(canvas, true)

    const ROTATE_SPEED = 0.0015

    let dragging = false
    let lastX = 0
    let lastY = 0

    const onDown = (e: PointerEvent) => {
      if (e.button === 0 || e.button === 2) {
        dragging = true
        lastX = e.clientX
        lastY = e.clientY
        canvas.setPointerCapture(e.pointerId)
      }
    }

    const onMove = (e: PointerEvent) => {
      if (!dragging) return
      const dx = e.clientX - lastX
      const dy = e.clientY - lastY
      lastX = e.clientX
      lastY = e.clientY

      // both buttons rotate — left look-around, right fixes facing direction (WoW flying)
      cam.rotation.y += dx * ROTATE_SPEED
      cam.rotation.x += dy * ROTATE_SPEED
      cam.rotation.x = Math.max(-Math.PI / 2 + 0.05, Math.min(Math.PI / 2 - 0.05, cam.rotation.x))
    }

    const onUp = () => { dragging = false }

    canvas.addEventListener('pointerdown', onDown)
    canvas.addEventListener('pointermove', onMove)
    canvas.addEventListener('pointerup',   onUp)
    canvas.addEventListener('contextmenu', e => e.preventDefault())
  }

  async loadMap(pack: MapPack): Promise<void> {
    this.scene.getMeshByName('fallback-ground')?.dispose()

    const basePath = pack.basePath.replace(/\/$/, '')
    const load = (path: string) =>
      SceneLoader.ImportMeshAsync('', basePath + '/', path, this.scene)

    const assets = pack.manifest.assets

    const [terrainResult, roadsResult, buildingsResult, vegResult, lod1Result, lod2Result] =
      await Promise.all([
        load(assets.terrain),
        load(assets.roads),
        load(assets.buildings),
        assets.vegetation ? load(assets.vegetation) : Promise.resolve(null),
        assets.terrainLod1 ? load(assets.terrainLod1) : Promise.resolve(null),
        assets.terrainLod2 ? load(assets.terrainLod2) : Promise.resolve(null),
      ])

    // ── Terrain LOD ────────────────────────────────────────────────────────
    const LOD1_DIST = 500    // metres from camera to tile centre
    const LOD2_DIST = 2000

    const lod1Tiles = lod1Result?.meshes ?? []
    const lod2Tiles = lod2Result?.meshes ?? []
    lod1Tiles.forEach(m => m.setEnabled(false))
    lod2Tiles.forEach(m => m.setEnabled(false))

    // Extract the satellite texture embedded in the glTF PBR material (if present),
    // then apply a StandardMaterial — PBR is sometimes not rendered on all tile meshes
    // by BabylonJS's glTF loader, and StandardMaterial is more reliable.
    const pbrMat = terrainResult.materials?.[0] as any
    const albedoTex: Texture | null = pbrMat?.albedoTexture ?? null

    const terrainMat = new StandardMaterial('terrain-mat', this.scene)
    terrainMat.backFaceCulling = false
    if (albedoTex) {
      terrainMat.diffuseTexture = albedoTex
    } else {
      terrainMat.diffuseColor = new Color3(0.35, 0.45, 0.25)
    }

    terrainResult.meshes.forEach((tile, i) => {
      tile.material = terrainMat
      if (lod1Tiles[i]) (tile as Mesh).addLODLevel(LOD1_DIST, lod1Tiles[i] as Mesh)
      if (lod2Tiles[i]) (tile as Mesh).addLODLevel(LOD2_DIST, lod2Tiles[i] as Mesh)
    })

    // ── Road colours ───────────────────────────────────────────────────────
    const roadColors: Record<string, Color3> = {
      road_major: new Color3(0.20, 0.20, 0.24),
      road_main:  new Color3(0.25, 0.25, 0.28),
      road_local: new Color3(0.30, 0.30, 0.33),
      road_small: new Color3(0.35, 0.35, 0.37),
      path:       new Color3(0.55, 0.48, 0.40),
    }
    const defaultRoadColor = new Color3(0.25, 0.25, 0.28)
    roadsResult.meshes.forEach(m => {
      const typeName = m.material?.name ?? m.name
      const mat = new StandardMaterial(`road-mat-${typeName}`, this.scene)
      mat.diffuseColor = roadColors[typeName] ?? defaultRoadColor
      m.material = mat
    })

    const buildingMat = new StandardMaterial('building-mat', this.scene)
    buildingMat.diffuseColor = new Color3(0.85, 0.78, 0.65)
    buildingsResult.meshes.forEach(m => { m.material = buildingMat })

    if (vegResult) {
      const vegMat = new StandardMaterial('vegetation-mat', this.scene)
      vegMat.diffuseColor = new Color3(0.15, 0.45, 0.12)
      vegResult.meshes.forEach(m => { m.material = vegMat })
    }
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
