const STEPS = [
  // ── Step 0 — System check ────────────────────────────────────────────────
  {
    title: 'System check',
    desc:  'Run this script from your Brelly project root to see what\'s already installed. Paste the output to pre-fill your progress and jump straight to the first missing step.',
    macos: [
      { type: 'instruction', label: 'Run in terminal from the Brelly project root', lang: 'bash',
        code: `bash pipeline/check_system.sh` },
      { type: 'checker-input' },
    ],
    windows: [
      { type: 'instruction', label: 'Run in PowerShell from the Brelly project root', lang: 'powershell',
        code: `.\\pipeline\\check_system.ps1` },
      { type: 'checker-input' },
    ],
  },

  // ── Step 1 ──────────────────────────────────────────────────────────────
  {
    title: 'Install package manager',
    desc:  'The package manager lets you install system tools like GDAL and Python with a single command.',
    precheck: {
      macos:   { lang: 'bash',        code: `brew --version`,   verify: `Homebrew 4.x.x` },
      windows: null,
    },
    macos: [
      { type: 'instruction', label: 'Run in terminal', lang: 'bash',
        code: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` },
      { type: 'callout', html: `After install, Homebrew prints two commands to add itself to your PATH. <strong>Run those too.</strong> They look like:<br><br>
<code>echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile</code><br>
<code>eval "$(/opt/homebrew/bin/brew shellenv)"</code>` },
      { type: 'instruction', label: 'Verify', lang: 'bash', code: `brew --version` },
      { type: 'verify', code: `Homebrew 4.x.x` },
    ],
    windows: [
      { type: 'callout', html: `<strong>No package manager needed on Windows.</strong> Python is installed directly via its official installer, which handles PATH setup for you. Continue to the next step.` },
    ],
  },

  // ── Step 2 ──────────────────────────────────────────────────────────────
  {
    title: 'Install Python 3.12',
    desc:  'GDAL binary wheels are only available for Python 3.10–3.12. If you already have a different version, that\'s fine — 3.12 installs alongside it and this guide uses it explicitly.',
    precheck: {
      macos:   { lang: 'bash',       code: `python3 --version      # active default\npython3.12 --version  # 3.12 specifically`, verify: `Python 3.x.x  # whatever is active\nPython 3.12.x  # must print this to skip` },
      windows: { lang: 'powershell', code: `python --version  # active default\npy --list        # all installed versions`, verify: `Python 3.x.x  # whatever is active\n-3.12-64  # must appear to skip` },
    },
    macos: [
      { type: 'instruction', label: 'Install alongside any existing Python', lang: 'bash', code: `brew install python@3.12` },
      { type: 'instruction', label: 'Verify', lang: 'bash', code: `python3.12 --version` },
      { type: 'verify', code: `Python 3.12.x` },
      { type: 'callout', html: `Your existing Python and any other tools are unaffected. All commands in this guide use <code>python3.12</code> explicitly, never the system default.` },
    ],
    windows: [
      { type: 'instruction', label: 'Download and install', html: `<ol>
<li>Go to <a href="https://www.python.org/downloads/release/python-3128/" target="_blank" style="color:var(--amber)">python.org/downloads/release/python-3128</a></li>
<li>Download <strong>Windows installer (64-bit)</strong></li>
<li>Run the installer — you can leave "Add python.exe to PATH" unchecked if another Python already owns it</li>
</ol>` },
      { type: 'instruction', label: 'Verify with the Python Launcher (open a new PowerShell window)', lang: 'powershell', code: `py -3.12 --version` },
      { type: 'verify', code: `Python 3.12.x` },
      { type: 'callout', html: `The <code>py</code> launcher selects the right version regardless of which Python owns your PATH. Subsequent steps use <code>py -3.12</code> for the same reason.` },
    ],
  },

  // ── Step 3 ──────────────────────────────────────────────────────────────
  {
    title: 'Install GDAL',
    desc:  'GDAL is the geospatial library used to read map data files.',
    precheck: {
      macos:   { lang: 'bash',       code: `gdal-config --version`, verify: `3.x.x` },
      windows: { lang: 'powershell', code: `py -3.12 -c "from osgeo import gdal; print(gdal.__version__)"`, verify: `3.x.x` },
    },
    macos: [
      { type: 'instruction', label: 'Run in terminal', lang: 'bash', code: `brew install gdal` },
      { type: 'instruction', label: 'Verify', lang: 'bash', code: `gdal-config --version` },
      { type: 'verify', code: `3.x.x` },
    ],
    windows: [
      { type: 'callout', html: `<strong>Do not use <code>pip install gdal</code> on Windows</strong> — it requires compiling from source and will fail. Use the pre-built wheel below instead.` },
      { type: 'instruction', label: 'Install via pre-built wheel', lang: 'powershell',
        code: `pip install gdal --find-links https://github.com/cgohlke/geospatial-wheels/releases` },
      { type: 'callout', html: `If that fails, download the <code>.whl</code> manually:<br><br>
1. Go to <a href="https://github.com/cgohlke/geospatial-wheels/releases" target="_blank" style="color:var(--amber)">github.com/cgohlke/geospatial-wheels/releases</a><br>
2. Download the file matching your Python — e.g. <code>GDAL-3.x.x-cp312-cp312-win_amd64.whl</code><br>
3. Run: <code>pip install C:\\Users\\you\\Downloads\\GDAL-3.x.x-cp312-cp312-win_amd64.whl</code>` },
      { type: 'instruction', label: 'Verify', lang: 'powershell', code: `python -c "from osgeo import gdal; print(gdal.__version__)"` },
      { type: 'verify', code: `3.x.x` },
    ],
  },

  // ── Step 4 ──────────────────────────────────────────────────────────────
  {
    title: 'Create a virtual environment',
    desc:  'A virtual environment keeps the pipeline\'s Python packages isolated from the rest of your system — so nothing conflicts and nothing breaks when you update other tools.',
    precheck: {
      macos:   { lang: 'bash',       code: `ls .venv/bin/python3`,           verify: `.venv/bin/python3` },
      windows: { lang: 'powershell', code: `Test-Path .venv\\Scripts\\python.exe`, verify: `True` },
    },
    macos: [
      { type: 'instruction', label: 'Run in terminal', lang: 'bash',
        code: `cd /path/to/Brelly\npython3.12 -m venv .venv\nsource .venv/bin/activate` },
      { type: 'callout', html: `Your prompt will now show <code>(.venv)</code>. All <code>pip</code> and <code>python</code> commands from here on run inside this environment.<br><br>
To deactivate later: <code>deactivate</code><br>
To reactivate in a new terminal: <code>source .venv/bin/activate</code>` },
      { type: 'verify', code: `# Your prompt should look like:\n(.venv) user@machine Brelly %` },
    ],
    windows: [
      { type: 'instruction', label: 'Run in PowerShell', lang: 'powershell',
        code: `cd C:\\path\\to\\Brelly\npy -3.12 -m venv .venv\n.venv\\Scripts\\Activate.ps1` },
      { type: 'callout', html: `If you get an error about execution policy, run this once first:<br><br>
<code>Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser</code><br><br>
To deactivate later: <code>deactivate</code><br>
To reactivate: <code>.venv\\Scripts\\Activate.ps1</code>` },
      { type: 'verify', code: `# Your prompt should look like:\n(.venv) PS C:\\path\\to\\Brelly>` },
    ],
  },

  // ── Step 5 ──────────────────────────────────────────────────────────────
  {
    title: 'Install Python dependencies',
    desc:  'Install the Python packages the pipeline uses for reading geospatial data, coordinate transforms, and geometry operations.',
    precheck: {
      macos:   { lang: 'bash',       code: `.venv/bin/python3 -c "from osgeo import gdal; import pyproj, shapely, numpy; print('OK')"`, verify: `OK` },
      windows: { lang: 'powershell', code: `.venv\\Scripts\\python.exe -c "from osgeo import gdal; import pyproj, shapely, numpy; print('OK')"`, verify: `OK` },
    },
    macos: [
      { type: 'instruction', label: 'Run in terminal — from the Brelly project root, venv active', lang: 'bash',
        code: `cd /path/to/Brelly\npip install -r pipeline/requirements.txt` },
      { type: 'callout', html: `If <code>gdal</code> fails, pin it to match the system GDAL:<br><br>
<code>pip install gdal==$(gdal-config --version) pyproj shapely numpy pytest</code>` },
      { type: 'instruction', label: 'Verify', lang: 'bash',
        code: `python -c "from osgeo import gdal; print(gdal.__version__)"\npython -c "import pyproj, shapely, numpy; print('OK')"` },
      { type: 'verify', code: `3.x.x\nOK` },
    ],
    windows: [
      { type: 'callout', html: `GDAL was already installed in Step 3. Install the remaining packages separately:` },
      { type: 'instruction', label: 'Run in PowerShell — from the Brelly project root, venv active', lang: 'powershell',
        code: `cd C:\\path\\to\\Brelly\npip install pyproj shapely numpy pytest` },
      { type: 'instruction', label: 'Verify', lang: 'powershell',
        code: `python -c "from osgeo import gdal; print(gdal.__version__)"\npython -c "import pyproj, shapely, numpy; print('OK')"` },
      { type: 'verify', code: `3.x.x\nOK` },
    ],
  },

  // ── Step 6 ──────────────────────────────────────────────────────────────
  {
    title: 'Install Blender',
    desc:  'Blender bakes 3-D meshes for terrain, roads, and buildings. Without it the pipeline still runs but produces empty placeholder geometry.',
    precheck: { lang: 'bash', code: `blender --version`, verify: `Blender 4.x.x` },
    macos: [
      { type: 'instruction', label: 'Download and install', html: `<ol>
<li>Go to <a href="https://www.blender.org/download/" target="_blank" style="color:var(--amber)">blender.org/download</a></li>
<li>Download the macOS <strong>.dmg</strong> and install as usual</li>
</ol>` },
      { type: 'instruction', label: 'Add Blender to PATH', lang: 'bash',
        code: `echo 'export PATH="/Applications/Blender.app/Contents/MacOS:$PATH"' >> ~/.zprofile\nsource ~/.zprofile` },
      { type: 'instruction', label: 'Verify', lang: 'bash', code: `blender --version` },
      { type: 'verify', code: `Blender 4.x.x` },
    ],
    windows: [
      { type: 'instruction', label: 'Download and install', html: `<ol>
<li>Go to <a href="https://www.blender.org/download/" target="_blank" style="color:var(--amber)">blender.org/download</a></li>
<li>Download the Windows <strong>.msi</strong> and run it</li>
</ol>` },
      { type: 'instruction', label: 'Add Blender to PATH', html: `<ol>
<li>Press <strong>Win + R</strong>, type <code>sysdm.cpl</code>, press Enter</li>
<li>Go to <strong>Advanced → Environment Variables</strong></li>
<li>Under <em>User variables</em>, select <strong>Path → Edit → New</strong></li>
<li>Add: <code>C:\\Program Files\\Blender Foundation\\Blender 4.x</code> (match your version)</li>
<li>Click OK on all dialogs, then open a <strong>new</strong> PowerShell window</li>
</ol>` },
      { type: 'instruction', label: 'Verify (new PowerShell window)', lang: 'powershell', code: `blender --version` },
      { type: 'verify', code: `Blender 4.x.x` },
    ],
  },

  // ── Step 7 ──────────────────────────────────────────────────────────────
  {
    title: 'Install gltfpack (optional)',
    desc:  'gltfpack compresses the .glb mesh files produced by the pipeline. Skip this step if you don\'t need smaller output files — the pipeline will warn but still run.',
    precheck: { lang: 'bash', code: `gltfpack --version`, verify: `meshoptimizer ...` },
    macos: [
      { type: 'instruction', label: 'Run in terminal', lang: 'bash', code: `brew install meshoptimizer` },
      { type: 'instruction', label: 'Verify', lang: 'bash', code: `gltfpack --version` },
      { type: 'callout', html: `If <code>brew install meshoptimizer</code> fails, download a prebuilt binary from <a href="https://github.com/zeux/meshoptimizer/releases" target="_blank" style="color:var(--amber)">github.com/zeux/meshoptimizer/releases</a> and place <code>gltfpack</code> somewhere on your PATH (e.g. <code>/usr/local/bin/gltfpack</code>).` },
    ],
    windows: [
      { type: 'instruction', label: 'Download and install', html: `<ol>
<li>Go to <a href="https://github.com/zeux/meshoptimizer/releases" target="_blank" style="color:var(--amber)">github.com/zeux/meshoptimizer/releases</a></li>
<li>Download <code>gltfpack-win64.exe</code> from the latest release</li>
<li>Rename to <code>gltfpack.exe</code> and place it in a folder on your PATH (e.g. <code>C:\\tools\\</code>)</li>
<li>Add that folder to PATH using the same steps as for Blender in Step 6</li>
</ol>` },
      { type: 'instruction', label: 'Verify (new PowerShell window)', lang: 'powershell', code: `gltfpack --version` },
    ],
  },

  // ── Step 8 ──────────────────────────────────────────────────────────────
  {
    title: 'Download source data',
    desc:  'The pipeline needs two datasets from swisstopo — Switzerland\'s federal geospatial authority. Both are free to download.',
    precheck: {
      macos:   { lang: 'bash',       code: `ls data/alti3d.tif data/swissTLM3D.gpkg`,                            verify: `data/alti3d.tif\ndata/swissTLM3D.gpkg` },
      windows: { lang: 'powershell', code: `Test-Path data\\alti3d.tif; Test-Path data\\swissTLM3D.gpkg`, verify: `True\nTrue` },
    },
    macos: [],
    windows: [],
    shared: [
      { type: 'instruction', label: 'alti3D — digital elevation model', html: `<ol>
<li>Go to <a href="https://www.swisstopo.admin.ch/en/height-model-swissalti3d" target="_blank" style="color:var(--amber)">swisstopo.admin.ch — alti3D</a></li>
<li>Download the GeoTIFF for your area (0.5 m resolution, LV95)</li>
<li>Save as <code>data/alti3d.tif</code> inside the Brelly project folder</li>
</ol>` },
      { type: 'instruction', label: 'swissTLM3D — topographic landscape model', html: `<ol>
<li>Go to <a href="https://www.swisstopo.admin.ch/en/landscape-model-swisstlm3d" target="_blank" style="color:var(--amber)">swisstopo.admin.ch — swissTLM3D</a></li>
<li>Download the GeoPackage (<code>.gpkg</code>) — full dataset or regional extract</li>
<li>Save as <code>data/swissTLM3D.gpkg</code> inside the Brelly project folder</li>
</ol>` },
      { type: 'verify', code: `Brelly/\n└── data/\n    ├── alti3d.tif\n    └── swissTLM3D.gpkg` },
    ],
  },

  // ── Step 9 ──────────────────────────────────────────────────────────────
  {
    title: 'Create a map config',
    desc:  'Each map area needs a JSON config file that defines its location, size, and race layout. Copy the example and fill in your values.',
    precheck: {
      macos:   { lang: 'bash',       code: `ls pipeline/config/*.json | grep -v example`,                                    verify: `pipeline/config/my_area.json` },
      windows: { lang: 'powershell', code: `Get-ChildItem pipeline\\config\\*.json | Where-Object Name -ne example.json`, verify: `my_area.json` },
    },
    macos: [
      { type: 'instruction', label: 'Copy the example config', lang: 'bash',
        code: `cp pipeline/config/example.json pipeline/config/my_area.json` },
    ],
    windows: [
      { type: 'instruction', label: 'Copy the example config', lang: 'powershell',
        code: `copy pipeline\\config\\example.json pipeline\\config\\my_area.json` },
    ],
    shared: [
      { type: 'instruction', label: 'Open the file and edit these fields', html: `<table style="width:100%;border-collapse:collapse;font-size:13px">
<tr style="border-bottom:1px solid var(--border)"><th style="text-align:left;padding:6px 8px;color:var(--text-3);font-weight:600">Field</th><th style="text-align:left;padding:6px 8px;color:var(--text-3);font-weight:600">What to set</th></tr>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">name</td><td style="padding:6px 8px;color:var(--text-3)">Short ID, no spaces — becomes the output folder name</td></tr>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">displayName</td><td style="padding:6px 8px;color:var(--text-3)">Human-readable name shown in the UI</td></tr>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">center_e</td><td style="padding:6px 8px;color:var(--text-3)">LV95 easting of your map centre</td></tr>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">center_n</td><td style="padding:6px 8px;color:var(--text-3)">LV95 northing of your map centre</td></tr>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">radius_m</td><td style="padding:6px 8px;color:var(--text-3)">Half-width in metres (500 = 1 km × 1 km)</td></tr>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">base_elevation</td><td style="padding:6px 8px;color:var(--text-3)">Approximate ground elevation at centre (metres)</td></tr>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">source_data.dem</td><td style="padding:6px 8px;color:var(--text-3)">Path to your alti3D GeoTIFF</td></tr>
<tr><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">source_data.tlm</td><td style="padding:6px 8px;color:var(--text-3)">Path to your swissTLM3D GeoPackage</td></tr>
</table>` },
      { type: 'callout', html: `To find LV95 coordinates for a location: go to <a href="https://map.geo.admin.ch" target="_blank" style="color:var(--amber)">map.geo.admin.ch</a> and right-click any point to copy coordinates.` },
    ],
  },

  // ── Step 10 ──────────────────────────────────────────────────────────────
  {
    title: 'Run the pipeline',
    desc:  'Run all 8 processing steps in sequence. The pipeline clips geodata, bakes 3-D meshes, builds the road graph, and assembles the manifest.',
    macos: [
      { type: 'callout', html: `Make sure the virtual environment is active: <code>source .venv/bin/activate</code>` },
      { type: 'instruction', label: 'Run in terminal', lang: 'bash',
        code: `python pipeline/run_pipeline.py pipeline/config/my_area.json` },
    ],
    windows: [
      { type: 'callout', html: `Make sure the virtual environment is active: <code>.venv\\Scripts\\Activate.ps1</code>` },
      { type: 'instruction', label: 'Run in PowerShell', lang: 'powershell',
        code: `python pipeline\\run_pipeline.py pipeline\\config\\my_area.json` },
    ],
    shared: [
      { type: 'verify', code: `============================================================\nRunning: scripts/01_reproject.py\n============================================================\nReprojected data clipped to bbox → maps/my_area/reprojected.gpkg\n...\nPipeline complete.` },
      { type: 'instruction', label: 'Output files', html: `<p>Results land in <code>maps/my_area/</code>:</p>
<ul style="margin-top:8px">
<li><code>terrain.glb</code> — heightmap mesh</li>
<li><code>roads.glb</code> — road surfaces</li>
<li><code>buildings.glb</code> — building footprints</li>
<li><code>vegetation.json</code> — tree positions</li>
<li><code>road-graph.json</code> — navigation graph</li>
<li><code>manifest.json</code> — map descriptor</li>
</ul>` },
    ],
  },

  // ── Step 11 ──────────────────────────────────────────────────────────────
  {
    title: 'Run the tests',
    desc:  'Verify the pipeline code is working correctly. All tests should pass with or without GDAL and Blender installed.',
    precheck: { lang: 'bash', code: `pytest pipeline/tests/ --tb=no -q`, verify: `25 passed` },
    macos: [
      { type: 'instruction', label: 'Run in terminal (venv must be active)', lang: 'bash',
        code: `pytest pipeline/tests/` },
    ],
    windows: [
      { type: 'instruction', label: 'Run in PowerShell (venv must be active)', lang: 'powershell',
        code: `pytest pipeline\\tests\\` },
    ],
    shared: [
      { type: 'verify', code: `collected 4 items\n\npipeline/tests/test_coords.py    PASSED\npipeline/tests/test_manifest.py  PASSED\npipeline/tests/test_road_graph.py PASSED\npipeline/tests/test_e2e.py       PASSED\n\n4 passed in 0.xx s` },
    ],
  },
];
