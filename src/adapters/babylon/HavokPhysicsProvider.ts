// src/adapters/babylon/HavokPhysicsProvider.ts
import {
  Scene,
  Vector3,
  MeshBuilder,
  PhysicsAggregate,
  PhysicsShapeType,
  HavokPlugin,
} from '@babylonjs/core'
import type { IPhysicsProvider, InputState, VehicleState, VehicleConfig } from '@core/types'

export class HavokPhysicsProvider implements IPhysicsProvider {
  private chassis: PhysicsAggregate
  private plugin: HavokPlugin
  private vehicleId: unknown = null
  private scene: Scene
  private config: VehicleConfig

  constructor(scene: Scene, config: VehicleConfig, spawnPosition: { x: number; y: number; z: number }) {
    this.scene = scene
    this.config = config

    const havokPlugin = scene.getPhysicsEngine()?.getPhysicsPlugin()
    if (!havokPlugin || !(havokPlugin instanceof HavokPlugin)) {
      throw new Error('HavokPhysicsProvider requires a HavokPlugin physics engine on the scene')
    }
    this.plugin = havokPlugin

    // Create chassis mesh (invisible — renderer draws its own visual mesh)
    const chassisMesh = MeshBuilder.CreateBox(
      'chassis-physics',
      { width: config.trackWidth, height: 0.5, depth: config.wheelBase + 1 },
      scene
    )
    chassisMesh.isVisible = false
    chassisMesh.position = new Vector3(spawnPosition.x, spawnPosition.y + 0.5, spawnPosition.z)

    this.chassis = new PhysicsAggregate(
      chassisMesh,
      PhysicsShapeType.BOX,
      { mass: config.mass, restitution: 0.0, friction: 0.8 },
      scene
    )

    this.initVehicle()
  }

  private initVehicle(): void {
    const hp = (this.plugin as unknown as { _hknp: Record<string, unknown> })._hknp
    if (!hp || typeof hp.HP_Vehicle_Create !== 'function') {
      // Havok vehicle API not available — fall back to force-based movement
      return
    }

    const bodyId = (this.chassis.body as unknown as { _pluginData: { hpBodyId: unknown } })
      ._pluginData.hpBodyId
    this.vehicleId = (hp.HP_Vehicle_Create as (id: unknown) => unknown)(bodyId)

    const halfTrack = this.config.trackWidth / 2
    const halfBase = this.config.wheelBase / 2
    const wheelPositions = [
      [-halfTrack, 0, halfBase],   // FL
      [halfTrack, 0, halfBase],    // FR
      [-halfTrack, 0, -halfBase],  // RL
      [halfTrack, 0, -halfBase],   // RR
    ]

    const addWheel = hp.HP_Vehicle_AddWheel as (
      vehicleId: unknown,
      pos: [number, number, number],
      suspensionDir: [number, number, number],
      axleDir: [number, number, number],
      suspensionLength: number,
      radius: number
    ) => void

    wheelPositions.forEach(([x, y, z]) => {
      addWheel(
        this.vehicleId,
        [x!, y!, z!],
        [0, -1, 0],
        [1, 0, 0],
        this.config.suspensionRestLength,
        0.35
      )
    })
  }

  applyInput(input: InputState): void {
    const hp = (this.plugin as unknown as { _hknp: Record<string, unknown> })._hknp
    if (!hp || !this.vehicleId) {
      this.applyForceFallback(input)
      return
    }

    const setEngine = hp.HP_Vehicle_SetEngineInput as (
      vehicleId: unknown, throttle: number, brake: number
    ) => void
    const setSteering = hp.HP_Vehicle_SetSteeringInput as (
      vehicleId: unknown, steer: number
    ) => void

    setEngine(this.vehicleId, input.throttle * this.config.engineForce, input.brake * this.config.brakeForce)
    setSteering(this.vehicleId, input.steer * this.config.maxSteeringAngle)
  }

  private applyForceFallback(input: InputState): void {
    const body = this.chassis.body
    const transform = body.transformNode
    const forward = new Vector3(0, 0, 1)
    const worldForward = Vector3.TransformNormal(
      forward,
      transform.getWorldMatrix()
    )
    const driveForce = worldForward.scale(
      (input.throttle - input.brake) * this.config.engineForce
    )
    body.applyForce(driveForce, transform.getAbsolutePosition())

    const torque = new Vector3(0, -input.steer * this.config.engineForce * 0.5, 0)
    body.applyAngularImpulse(torque)
  }

  step(_dt: number): void {
    // Havok steps automatically each scene render via the physics plugin.
  }

  getVehicleState(): VehicleState {
    const body = this.chassis.body
    const pos = body.transformNode.getAbsolutePosition()
    const rotQ = body.transformNode.rotationQuaternion ?? { x: 0, y: 0, z: 0, w: 1 }
    const vel = body.getLinearVelocity()
    const speed = vel.length() * 3.6 // m/s → kph

    return {
      position: { x: pos.x, y: pos.y, z: pos.z },
      rotation: { x: rotQ.x, y: rotQ.y, z: rotQ.z, w: rotQ.w },
      velocityKph: speed,
      steeringAngle: 0,
      wheelContacts: [true, true, true, true],
    }
  }

  dispose(): void {
    const hp = (this.plugin as unknown as { _hknp: Record<string, unknown> })._hknp
    if (hp && this.vehicleId && typeof hp.HP_Vehicle_Destroy === 'function') {
      (hp.HP_Vehicle_Destroy as (id: unknown) => void)(this.vehicleId)
    }
    this.chassis.dispose()
  }
}
