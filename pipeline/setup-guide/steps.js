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
    precheck: { lang: 'bash', code: `command -v gltfpack`, verify: `/usr/local/bin/gltfpack` },
    macos: [
      { type: 'instruction', label: 'Download the binary', html: `<ol>
<li>Go to <a href="https://github.com/zeux/meshoptimizer/releases" target="_blank" style="color:var(--amber)">github.com/zeux/meshoptimizer/releases</a></li>
<li>Download <code>gltfpack-macos</code> from the latest release</li>
<li>Rename it and move it onto your PATH:</li>
</ol>` },
      { type: 'instruction', label: 'Install', lang: 'bash', code: `sudo mv ~/Downloads/gltfpack /usr/local/bin/gltfpack\nsudo chmod +x /usr/local/bin/gltfpack\nsudo xattr -d com.apple.quarantine /usr/local/bin/gltfpack` },
      { type: 'instruction', label: 'Verify', lang: 'bash', code: `gltfpack --version` },
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
      macos:   { lang: 'bash',       code: `ls data/{AREA}/alti3d.vrt data/{AREA}/swissTLM3D.gpkg`,         verify: `data/{AREA}/alti3d.vrt\ndata/{AREA}/swissTLM3D.gpkg` },
      windows: { lang: 'powershell', code: `Test-Path data\\{AREA}\\alti3d.vrt; Test-Path data\\{AREA}\\swissTLM3D.gpkg`, verify: `True\nTrue` },
    },
    macos: [
      { type: 'area-input' },
      { type: 'instruction', label: 'Create the area folder', lang: 'bash',
        code: `mkdir -p data/{AREA}` },
      { type: 'instruction', label: 'Build the VRT mosaic (run after placing all .tif tiles)', lang: 'bash',
        code: `gdalbuildvrt data/{AREA}/alti3d.vrt data/{AREA}/*.tif` },
    ],
    windows: [
      { type: 'area-input' },
      { type: 'instruction', label: 'Create the area folder', lang: 'powershell',
        code: `mkdir data\\{AREA}` },
      { type: 'instruction', label: 'Build the VRT mosaic (run after placing all .tif tiles)', lang: 'powershell',
        code: `$tiles = (Get-ChildItem data\\{AREA}\\*.tif).FullName\ngdalbuildvrt data\\{AREA}\\alti3d.vrt $tiles` },
    ],
    shared: [
      { type: 'instruction', label: 'alti3D — digital elevation model', html: `<ol>
<li>Go to <a href="https://www.swisstopo.admin.ch/en/height-model-swissalti3d" target="_blank" style="color:var(--amber)">swisstopo.admin.ch — alti3D</a></li>
<li>Download all GeoTIFF tiles covering your area (0.5 m resolution, LV95)</li>
<li>Place all <code>.tif</code> files into <code>data/{AREA}/</code> — names don't matter, any <code>*.tif</code> in that folder is included</li>
</ol>` },
      { type: 'callout', html: `swisstopo tile filenames look like <code>swissalti3d_0.5_2056_2680_1248.tif</code> — the numbers are the LV95 km-grid position. Tiles are georeferenced so GDAL aligns them automatically; you don't need to rename or reorder them.` },
      { type: 'instruction', label: 'swissTLM3D — topographic landscape model', html: `<ol>
<li>Go to <a href="https://www.swisstopo.admin.ch/en/landscape-model-swisstlm3d" target="_blank" style="color:var(--amber)">swisstopo.admin.ch — swissTLM3D</a></li>
<li>Click <strong>Download swissTLM3D</strong>, then choose format <strong>GeoPackage (.gpkg)</strong></li>
<li>There is only one file covering all of Switzerland — download it and save as <code>data/{AREA}/swissTLM3D.gpkg</code></li>
</ol>` },
      { type: 'verify', code: `Brelly/\n└── data/\n    └── {AREA}/\n        ├── swissalti3d_0.5_2056_2680_1248.tif  ← one or more tiles\n        ├── swissalti3d_0.5_2056_2681_1248.tif\n        ├── alti3d.vrt                          ← generated by gdalbuildvrt\n        └── swissTLM3D.gpkg` },
    ],
  },

  // ── Step 9 ──────────────────────────────────────────────────────────────
  {
    title: 'Create a map config',
    desc:  'Fill in your area details — the config file is generated and downloaded ready to use.',
    precheck: {
      macos:   { lang: 'bash',       code: `ls pipeline/config/*.json | grep -v example`,                                 verify: `# any non-example .json means this step is done` },
      windows: { lang: 'powershell', code: `Get-ChildItem pipeline\\config\\*.json | Where-Object Name -ne example.json`, verify: `# any file listed means this step is done` },
    },
    macos: [],
    windows: [],
    shared: [
      { type: 'config-builder' },
    ],
  },

  // ── Step 10 ──────────────────────────────────────────────────────────────
  {
    title: 'Run the pipeline',
    desc:  'Download the run script below — it activates the virtual environment and runs the pipeline in one step, with your area name already filled in.',
    macos: [
      { type: 'run-script' },
      { type: 'instruction', label: 'Run from the Brelly project folder', lang: 'bash',
        code: `bash run_{AREA}.sh` },
    ],
    windows: [
      { type: 'run-script' },
      { type: 'instruction', label: 'Run from the Brelly project folder', lang: 'powershell',
        code: `.\\run_{AREA}.ps1` },
    ],
    shared: [
      { type: 'verify', code: `============================================================\nRunning: scripts/01_reproject.py\n============================================================\nReprojected data clipped to bbox → maps/{AREA}/reprojected.gpkg\n...\nPipeline complete.` },
      { type: 'instruction', label: 'Output files', html: `<p>Results land in <code>maps/{AREA}/</code>:</p>
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
