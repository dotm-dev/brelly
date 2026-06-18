# Design: Pipeline Setup Guide (Interactive Web Page)

**Date:** 2026-06-18  
**Status:** Approved

---

## Goal

An interactive static web page that walks any user — technical or not — through setting up the Brelly map creation pipeline from a clean OS installation. No server, no build step: a single HTML file opened directly in a browser.

---

## Audience

All contributors: developers, artists, level designers. Beginner-friendly but not condescending. Assumes the user can open a browser and copy-paste terminal commands.

---

## File location

```
pipeline/setup-guide/index.html
```

Single self-contained file. Vanilla JS + inline CSS. No dependencies, no npm, no framework.

---

## Structure

**Wizard with sidebar overview.**  
Content is shown one step at a time. A sidebar lists all steps and current progress. Users can click any step in the sidebar to jump directly — no forced linear lock. Prev / Next buttons in the footer provide sequential navigation.

---

## OS handling

- On first load: full-screen OS picker (two cards: macOS, Windows).
- Selection stored in `localStorage` — persists across reloads.
- Active OS shown in a badge in the top bar: `OS: macOS · switch`.
- Clicking "switch" resets the OS selection and returns to the OS picker.
- Steps with platform-specific content render only the relevant branch. Steps identical on both OSes use a single content block.

---

## Layout

### Top bar (fixed)
- Left: `Brelly / Map Pipeline Setup` — title in amber.
- Right: OS badge with "switch" link.

### Sidebar (fixed, 240px)
- Progress bar + `X of 11 complete` label.
- Step list: each item shows step number (or ✓ when done) + label.
- Active step highlighted with amber left border and amber number badge.
- Completed steps show a green ✓.
- Clicking any step navigates to it.

### Main content (scrollable)
One step rendered at a time. Each step contains:
1. **Step tag** — `Step N of 11` in amber, small caps.
2. **Title** — large, white.
3. **Description** — secondary text explaining what this step does and why.
4. **Instruction blocks** — one or more, each with:
   - A label (`Run in terminal`, `In the installer`, etc.)
   - A code block with a **Copy** button.
5. **Callout notes** (optional) — amber left border, secondary info or warnings.
6. **Verify block** (optional) — green tint, shows expected terminal output so users can confirm the step worked.

### Footer nav (fixed)
- Left: `← Previous step name` button (hidden on step 1).
- Centre: `Step N of 11`.
- Right: `Next step name →` button (hidden on step 11, replaced by a "Done" state).

---

## Visual style

- **Background:** `#0f1117` (near-black)
- **Surface:** `#1a1d27` / `#13151f`
- **Accent:** `#f59e0b` (amber) — titles, active states, copy buttons, step tags
- **Success:** `#34d399` (green) — verify blocks, completed step indicators
- **Text:** `#e2e8f0` primary, `#94a3b8` secondary, `#4b5563` muted
- **Code:** monospace font, `#a3e635` green on dark background
- **Borders:** `#2a2d3a`

---

## State management

All state lives in `localStorage`:

| Key | Value | Description |
|-----|-------|-------------|
| `brelly-pipeline-os` | `"macos"` \| `"windows"` | Selected OS |
| `brelly-pipeline-step` | `0`–`10` (index) | Current step index |
| `brelly-pipeline-done` | JSON array of indices | Steps marked complete |

A step is marked done when the user clicks Next past it. Clicking a sidebar step does not mark anything done — only forward navigation does.

---

## Copy button behaviour

Uses `navigator.clipboard.writeText()`. On success, button label changes to `Copied!` for 1.5 s then resets to `Copy`. No fallback needed — all target browsers support the Clipboard API.

---

## Steps

11 steps, content sourced from `SETUP_MACOS.md` and `SETUP_WINDOWS.md`:

| # | Title | macOS | Windows |
|---|-------|-------|---------|
| 1 | Install package manager | Install Homebrew | *(no equivalent — Python installer handles PATH)* |
| 2 | Install Python 3.12 | `brew install python@3.12` | Download official installer; check "Add to PATH" |
| 3 | Install GDAL | `brew install gdal` | Download pre-built wheel from Gohlke's repo |
| 4 | Create virtual environment | `python3.12 -m venv .venv && source .venv/bin/activate` | `python -m venv .venv && .venv\Scripts\Activate.ps1` |
| 5 | Install Python dependencies | `pip install -r pipeline/requirements.txt` | `pip install pyproj shapely numpy pytest` + GDAL wheel |
| 6 | Install Blender | Download `.dmg`; add to PATH via `~/.zprofile` | Download `.msi`; add to PATH via System Properties |
| 7 | Install gltfpack (optional) | `brew install meshoptimizer` | Download binary from releases; add to PATH |
| 8 | Download source data | swisstopo alti3D + swissTLM3D — same on both OSes | same |
| 9 | Create map config | Copy example.json, edit fields — same on both | `copy` instead of `cp`; forward slashes in JSON |
| 10 | Run the pipeline | `python pipeline/run_pipeline.py config.json` | same |
| 11 | Run the tests | `pytest pipeline/tests/` | same |

Step 1 on Windows shows a note explaining there is no package manager step — Python is installed via the official installer directly.

---

## Out of scope

- Running pipeline commands from the browser (future).
- Config editor / form UI (future).
- Mobile layout (not a priority — this is a desktop dev tool).
- Dark/light theme toggle.
