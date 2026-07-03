# Quickstart

Just want to see a map? Follow these steps in order.

## 1. Install everything
- **Mac:** `bash pipeline/setup.sh`
- **Windows:** `.\pipeline\setup.ps1` — run this in **PowerShell** (not Command Prompt),
  ideally opened **as Administrator** (avoids extra permission prompts). If PowerShell
  refuses to run the script at all, first run once:
  `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

Wait for it to finish — this launches an app window when done.

## 2. Get map data
In the app that opened, click **+ New Map**, give your map a name, and select:
- your downloaded elevation `.tif` files
- your swissTLM3D file (roads/buildings/vegetation)

Don't have data yet? Download it here:
- Elevation: https://www.swisstopo.admin.ch/en/height-model-swissalti3d
- Roads/buildings: https://www.swisstopo.admin.ch/en/landscape-model-swisstlm3d

## 3. Build the map
In the app, go to the **Run** tab and click **Run**. Wait for it to finish (can take a while).

## 4. See it in the browser
```bash
npm install
npm run dev
```
Open `http://localhost:5173/?map=<your_map_name>` in your browser (use the exact name/case you gave your map in step 2) — it's ready to explore.

---
Need more detail? See [README.md](README.md).
