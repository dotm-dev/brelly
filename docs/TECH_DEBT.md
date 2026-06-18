# Tech Debt

## Plan 1 — Foundation

| ID | File | Issue | Fix |
|---|---|---|---|
| TD-01 | `src/adapters/babylon/BabylonRenderer.ts` | ~~Resize listener leak~~ | **Resolved in Plan 3** — `resizeHandler` stored as named field, removed in `dispose()`. |
| TD-02 | `src/adapters/babylon/BabylonScene.ts` | `WEBGL_debug_renderer_info` is deprecated in Firefox and will be removed. Please use `RENDERER`. Likely emitted by Babylon.js engine init. | Upgrade Babylon.js when a fix is available, or suppress via engine options if possible. Monitor in Plan 3. |
