# Tech Debt

## Plan 1 — Foundation

| ID | File | Issue | Fix |
|---|---|---|---|
| TD-01 | `src/adapters/babylon/BabylonScene.ts` | Resize event listener added in `setupResizeHandler()` is never removed in `dispose()` — will call `engine.resize()` on a disposed engine in teardown scenarios | Store handler ref, call `window.removeEventListener` in `dispose()`. Address in Plan 3 when adapter is properly wired. |
| TD-02 | `src/adapters/babylon/BabylonScene.ts` | `WEBGL_debug_renderer_info` is deprecated in Firefox and will be removed. Please use `RENDERER`. Likely emitted by Babylon.js engine init. | Upgrade Babylon.js when a fix is available, or suppress via engine options if possible. Monitor in Plan 3. |
