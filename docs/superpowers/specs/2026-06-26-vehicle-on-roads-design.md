# Vehicle on Roads — Design Spec
_Date: 2026-06-26_

## Goal

Enable the player to drive a physically-simulated vehicle freely over the generated map, using roads as the primary driveable surface. Falling into the void triggers a reset to the last known good position.

## Architecture

### Road Physics Colliders

- After loading the map GLB assets, `BabylonRenderer.loadMap()` identifies all road mesh nodes and attaches a `PhysicsAggregate` with shape `MESH` (static, mass=0) to each.
- Terrain, buildings, and vegetation remain visual-only (no colliders).
- This makes roads the only solid surface; driving off them results in the vehicle falling.

### Last-Good-Position Watchdog

- `GameApp` maintains two state vars: `lastGoodPosition: Vector3` and `lastGoodRotation: Quaternion`.
- A 0.5s interval timer runs alongside the game loop. Each tick: if `vehicleState.position.y > (base_elevation - 5)`, overwrite last-good state.
- Initial value is `manifest.spawnPosition` so the first reset always lands somewhere valid.

### Void Reset

- Each game loop tick checks if `vehicleState.position.y < (base_elevation - 10)`.
- If true, calls `physicsProvider.resetTo(lastGoodPosition, lastGoodRotation)` which teleports the vehicle and zeroes linear + angular velocity.
- A small upward offset (+1m) is added to the Y on reset to avoid clipping the road surface.

### Entry Point

- `GameApp.start(mapPack)` already exists and wires Havok + vehicle + game loop.
- `main.ts` currently calls `startPreview()` — it will be switched to `start()` with the map pack to enable physics mode.

## Out of Scope

- Terrain colliders (future)
- Building/vegetation colliders (future)
- Respawn animation or fade effect
- Road graph path guidance / AI assist
