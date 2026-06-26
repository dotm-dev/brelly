# Vehicle on Roads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable free-physics driving on road colliders with an automatic void-reset to the last known good position.

**Architecture:** Road GLB meshes get static Havok `MESH` colliders in `BabylonRenderer.loadMap()`. `GameApp.start()` adds a watchdog that saves position + rotation every 0.5 s when the vehicle is above a safe Y threshold, and teleports back there when the vehicle falls below a void threshold. `IPhysicsProvider` gains a `resetTo()` method implemented in `HavokPhysicsProvider`. `main.ts` is switched from `startPreview` to `start` when a map is provided.

**Tech Stack:** Babylon.js 7, `@babylonjs/havok`, TypeScript

---

### Task 1: Add `resetTo()` to `IPhysicsProvider` and `HavokPhysicsProvider`

**Files:**
- Modify: `src/core/types.ts`
- Modify: `src/adapters/babylon/HavokPhysicsProvider.ts`

- [ ] **Step 1: Add `resetTo` to the `IPhysicsProvider` interface in `src/core/types.ts`**

Find the interface (around line 80) and add one method:

```ts
export interface IPhysicsProvider {
  applyInput(input: InputState): void
  getVehicleState(): VehicleState
  step(dt: number): void
  resetTo(position: Vec3, rotation: Quat): void
  dispose(): void
}
```

- [ ] **Step 2: Implement `resetTo()` in `HavokPhysicsProvider`**

Add this method to `HavokPhysicsProvider` (before `dispose()`):

```ts
resetTo(position: Vec3, rotation: Quat): void {
  const body = this.chassis.body
  body.transformNode.position.set(position.x, position.y, position.z)
  body.transformNode.rotationQuaternion = new Quaternion(
    rotation.x, rotation.y, rotation.z, rotation.w
  )
  body.setLinearVelocity(Vector3.Zero())
  body.setAngularVelocity(Vector3.Zero())
}
```

Add `Quaternion` to the existing `@babylonjs/core` import at the top of the file.

- [ ] **Step 3: Verify TypeScript compiles**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/core/types.ts src/adapters/babylon/HavokPhysicsProvider.ts
git commit -m "feat: add resetTo() to IPhysicsProvider + HavokPhysicsProvider"
```

---

### Task 2: Add road physics colliders in `BabylonRenderer.loadMap()`

**Files:**
- Modify: `src/adapters/babylon/BabylonRenderer.ts`

Context: `loadMap()` is called after `scene.enablePhysics()` in `GameApp.start()`, so the physics engine is available. We add a static `MESH` collider to each road submesh.

- [ ] **Step 1: Add `PhysicsAggregate` and `PhysicsShapeType` to the Babylon import in `BabylonRenderer.ts`**

The existing import block already has many Babylon symbols. Add the two missing ones:

```ts
import {
  // ...existing imports...
  PhysicsAggregate,
  PhysicsShapeType,
} from '@babylonjs/core'
```

- [ ] **Step 2: After the road color assignment loop in `loadMap()`, add colliders to every road mesh**

Locate the block that ends with:
```ts
roadsResult.meshes.forEach(m => {
  const typeName = m.material?.name ?? m.name
  const mat = new StandardMaterial(`road-mat-${typeName}`, this.scene)
  mat.diffuseColor = roadColors[typeName] ?? defaultRoadColor
  m.material = mat
})
```

Immediately after that block, add:

```ts
roadsResult.meshes.forEach(m => {
  if (!(m instanceof Mesh) || m.getTotalVertices() === 0) return
  // Physics engine may not be active in preview mode — guard before adding aggregate
  if (!this.scene.getPhysicsEngine()) return
  new PhysicsAggregate(m, PhysicsShapeType.MESH, { mass: 0 }, this.scene)
})
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/adapters/babylon/BabylonRenderer.ts
git commit -m "feat: add static MESH physics colliders to road meshes"
```

---

### Task 3: Add void watchdog to `GameApp.start()`

**Files:**
- Modify: `src/adapters/babylon/GameApp.ts`

The watchdog runs on the game tick (not a separate interval). Every 0.5 s of accumulated time it checks if the vehicle Y is above `spawnY - 5` and saves the position; every tick it checks if Y is below `spawnY - 10` and triggers a reset.

- [ ] **Step 1: Add watchdog state variables and logic inside `GameApp.start()`**

Inside `start()`, after the `const spawnPos = ...` line, add:

```ts
// Void watchdog state
const VOID_THRESHOLD = spawnPos.y - 10    // fall this far → reset
const GOOD_THRESHOLD = spawnPos.y - 5     // above this → save position
let lastGoodPos: { x: number; y: number; z: number } = { ...spawnPos, y: spawnPos.y + 1 }
let lastGoodRot: { x: number; y: number; z: number; w: number } = mapPack?.manifest.spawnRotation ?? { x: 0, y: 0, z: 0, w: 1 }
let goodSaveAccum = 0
```

- [ ] **Step 2: Inside the render loop callback, add watchdog tick logic**

The existing render loop in `start()` is:

```ts
this.renderer.startRenderLoop(() => {
  const now = performance.now()
  const dt = Math.min((this.renderer.scene.deltaTime ?? 16) / 1000, 0.05)
  this.inputHandler.update()
  this.loop?.tick(dt, now)
})
```

Replace it with:

```ts
this.renderer.startRenderLoop(() => {
  const now = performance.now()
  const dt = Math.min((this.renderer.scene.deltaTime ?? 16) / 1000, 0.05)
  this.inputHandler.update()
  this.loop?.tick(dt, now)

  // Void watchdog
  const vState = sim.state
  if (vState.position.y < VOID_THRESHOLD) {
    physicsProvider.resetTo(lastGoodPos, lastGoodRot)
  } else {
    goodSaveAccum += dt
    if (goodSaveAccum >= 0.5 && vState.position.y > GOOD_THRESHOLD) {
      lastGoodPos = { ...vState.position }
      lastGoodRot = { ...vState.rotation }
      goodSaveAccum = 0
    }
  }
})
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/adapters/babylon/GameApp.ts
git commit -m "feat: void watchdog with last-good-position reset"
```

---

### Task 4: Switch `main.ts` from `startPreview` to `start` for map mode

**Files:**
- Modify: `src/main.ts`

Currently when a `?map=` query param is provided, `main.ts` calls `app.startPreview()`. We switch it to `app.start(mapPack)` so Havok physics is active and road colliders are registered.

- [ ] **Step 1: Replace the `startPreview` call with `start` in `main.ts`**

Current code:
```ts
Promise.all([
  fetch(`${base}/manifest.json`).then(r => r.json()),
  fetch(`${base}/road-graph.json`).then(r => r.json()),
]).then(([manifest, roadGraph]) => {
  app.startPreview({ basePath: base, manifest, roadGraph }).catch(console.error)
}).catch(err => {
  console.error('Failed to load map:', err)
})
```

Replace with:
```ts
Promise.all([
  fetch(`${base}/manifest.json`).then(r => r.json()),
  fetch(`${base}/road-graph.json`).then(r => r.json()),
]).then(([manifest, roadGraph]) => {
  app.start({ basePath: base, manifest, roadGraph }).catch(console.error)
}).catch(err => {
  console.error('Failed to load map:', err)
})
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add src/main.ts
git commit -m "feat: switch map mode from startPreview to start (physics enabled)"
```

---

### Task 5: Manual smoke test

- [ ] **Step 1: Start the dev server**

```bash
npm run dev
```

- [ ] **Step 2: Open the map in a browser**

Navigate to `http://localhost:5173/?map=bre` (or the port shown in the terminal).

- [ ] **Step 3: Verify the vehicle spawns on or near a road**

Expected: vehicle appears at `spawnPosition` from `manifest.json`, follow-camera is active, the vehicle rests on the road surface (not falling through).

- [ ] **Step 4: Drive off the road and confirm void reset**

Use WASD to drive off the edge of a road. The vehicle should fall, then after dropping ~10 m below spawn Y, teleport back to the last saved road position.

- [ ] **Step 5: Commit any fixes found during smoke test, then tag**

```bash
git tag v0.1-drive
```
