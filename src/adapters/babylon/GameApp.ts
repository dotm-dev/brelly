// src/adapters/babylon/GameApp.ts
import HavokPhysics from '@babylonjs/havok'
import { HavokPlugin, Vector3, MeshBuilder, PhysicsAggregate, PhysicsShapeType } from '@babylonjs/core'
import { BabylonRenderer } from './BabylonRenderer'
import { HavokPhysicsProvider } from './HavokPhysicsProvider'
import { InputHandler } from './InputHandler'
import { HUD } from './HUD'
import { EventBus } from '@core/EventBus'
import { InputState } from '@core/InputState'
import { VehicleSimulation } from '@core/VehicleSimulation'
import { RaceSession } from '@core/RaceSession'
import { GameLoop } from '@core/GameLoop'
import { MapModel } from '@core/MapModel'
import type { VehicleConfig, MapPack } from '@core/types'

const DEFAULT_VEHICLE_CONFIG: VehicleConfig = {
  mass: 1200,
  engineForce: 6000,
  brakeForce: 3000,
  maxSteeringAngle: 0.5,
  wheelBase: 2.7,
  trackWidth: 1.6,
  suspensionRestLength: 0.3,
  suspensionStiffness: 30,
  suspensionDamping: 2.3,
  meshPath: 'vehicle.glb',
}

export class GameApp {
  private renderer: BabylonRenderer
  private bus: EventBus
  private input: InputState
  private inputHandler: InputHandler
  private hud: HUD | null = null
  private loop: GameLoop | null = null


  constructor(private readonly canvas: HTMLCanvasElement) {
    this.bus = new EventBus()
    this.input = new InputState()
    this.inputHandler = new InputHandler(this.input)
    this.renderer = new BabylonRenderer(canvas)
  }

  async startPreview(mapPack: MapPack): Promise<void> {
    await this.renderer.loadMap(mapPack)
    this.renderer.attachPreviewControls(this.canvas)
    this.renderer.startRenderLoop(() => {})
  }

  async start(mapPack?: MapPack): Promise<void> {
    // Initialize Havok physics
    const havokInstance = await HavokPhysics()
    const havokPlugin = new HavokPlugin(true, havokInstance)
    this.renderer.scene.enablePhysics(new Vector3(0, -9.81, 0), havokPlugin)

    // Load map if provided, otherwise add physics collider to fallback ground
    if (mapPack) {
      await this.renderer.loadMap(mapPack)
    } else {
      const ground = MeshBuilder.CreateBox(
        'ground-collider',
        { width: 500, height: 0.2, depth: 500 },
        this.renderer.scene
      )
      ground.position.y = -0.1
      ground.isVisible = false
      new PhysicsAggregate(ground, PhysicsShapeType.BOX, { mass: 0 }, this.renderer.scene)
    }

    const spawnPos = mapPack?.manifest.spawnPosition ?? { x: 0, y: 1, z: 0 }

    // Spawn vehicle visual
    this.renderer.spawnVehicleMesh()

    // Create physics provider
    const physicsProvider = new HavokPhysicsProvider(
      this.renderer.scene,
      DEFAULT_VEHICLE_CONFIG,
      spawnPos
    )

    // Wire game core
    const sim = new VehicleSimulation(physicsProvider)
    const model = mapPack
      ? new MapModel(mapPack)
      : new MapModel(this.makeEmptyMapPack())
    const session = new RaceSession(model, this.bus)
    this.loop = new GameLoop(sim, session, this.input, this.bus)

    // HUD
    this.hud = new HUD(this.bus)

    // Subscribe vehicleUpdated → move visual mesh
    this.bus.on('vehicleUpdated', (state) => {
      this.renderer.updateVehicle(state)
      if (session.status === 'racing') {
        this.hud?.updateTimer(session.elapsedMs)
      }
    })

    // Start render loop — input + game tick happen before each render
    this.renderer.startRenderLoop(() => {
      const now = performance.now()
      const dt = Math.min((this.renderer.scene.deltaTime ?? 16) / 1000, 0.05)
      this.inputHandler.update()
      this.loop?.tick(dt, now)
    })
  }

  private makeEmptyMapPack(): MapPack {
    return {
      basePath: '',
      roadGraph: { nodes: [], edges: [] },
      manifest: {
        name: 'empty',
        displayName: 'Test Plane',
        spawnPosition: { x: 0, y: 1, z: 0 },
        spawnRotation: { x: 0, y: 0, z: 0, w: 1 },
        startLine: { position: { x: 0, y: 0, z: -5 }, normal: { x: 0, y: 0, z: 1 }, widthMetres: 10 },
        finishLine: { position: { x: 0, y: 0, z: 50 }, normal: { x: 0, y: 0, z: 1 }, widthMetres: 10 },
        checkpoints: [],
        assets: { terrain: '', roads: '', buildings: '', vegetationData: '' },
        roadGraph: '',
        bounds: { min: { x: -100, y: -5, z: -100 }, max: { x: 100, y: 50, z: 100 } },
      },
    }
  }

  dispose(): void {
    this.inputHandler.dispose()
    this.hud?.dispose()
    this.renderer.dispose()
    this.bus.dispose()
  }
}
