# Pipeline Setup Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single self-contained `pipeline/setup-guide/index.html` that walks any user through pipeline setup step-by-step, with OS-aware content, copyable commands, and persistent progress.

**Architecture:** Single HTML file with inline CSS and vanilla JS. No build step, no server, no dependencies — open directly in a browser. State (OS choice, current step, completed steps) lives in `localStorage`. All step content is defined in a JS data array; a render engine reads it and updates the DOM on navigation.

**Tech Stack:** HTML5, CSS3, vanilla JS (ES6+), `localStorage`, `navigator.clipboard`

---

## File Structure

```
pipeline/setup-guide/
└── index.html   ← entire app: markup shell + inline <style> + inline <script>
```

One file, built up across tasks. Each task adds to it; later tasks assume earlier ones are in place.

---

### Task 1: HTML scaffold + CSS foundation

**Files:**
- Create: `pipeline/setup-guide/index.html`

Build the complete CSS + empty HTML shell. No JS yet — just layout bones and design tokens.

- [ ] **Step 1: Create the file with doctype, meta, title, and CSS**

`pipeline/setup-guide/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Brelly — Map Pipeline Setup</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #0f1117;
  --surface-1: #13151f;
  --surface-2: #1a1d27;
  --surface-3: #1f2233;
  --border:    #2a2d3a;
  --text-1:    #f1f5f9;
  --text-2:    #e2e8f0;
  --text-3:    #94a3b8;
  --text-4:    #64748b;
  --text-5:    #4b5563;
  --amber:     #f59e0b;
  --amber-dim: #fbbf24;
  --green:     #34d399;
  --green-bg:  #0d1a12;
  --green-bdr: #1a3a25;
  --code-fg:   #a3e635;
  --code-bg:   #0d0f18;
  --sidebar-w: 240px;
  --topbar-h:  52px;
  --footer-h:  64px;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text-2);
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-size: 14px;
  overflow: hidden;
}

/* ── Top bar ── */
#topbar {
  height: var(--topbar-h);
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  z-index: 10;
}
#topbar-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--amber);
}
#topbar-title span { color: var(--text-3); font-weight: 400; }

#os-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface-3);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 12px;
  font-size: 12px;
  color: var(--text-3);
}
#os-badge strong { color: var(--text-2); }
#os-switch-btn {
  color: var(--amber);
  background: none;
  border: none;
  font-size: 11px;
  cursor: pointer;
  font-family: inherit;
  padding: 0;
}
#os-badge { display: none; } /* hidden until OS is chosen */

/* ── Body ── */
#body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── Sidebar ── */
#sidebar {
  width: var(--sidebar-w);
  background: var(--surface-1);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow-y: auto;
  display: none; /* hidden until OS is chosen */
}
.sidebar-section-label {
  padding: 16px 16px 8px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-5);
}
#progress-wrap {
  margin: 4px 16px 0;
  background: var(--surface-3);
  border-radius: 99px;
  height: 4px;
}
#progress-fill {
  height: 4px;
  border-radius: 99px;
  background: var(--amber);
  width: 0%;
  transition: width 0.3s ease;
}
#progress-label {
  margin: 6px 16px 12px;
  font-size: 11px;
  color: var(--text-5);
}
#step-list { list-style: none; }
.step-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: background 0.1s;
}
.step-item:hover { background: var(--surface-2); }
.step-item.active {
  background: var(--surface-3);
  border-left-color: var(--amber);
}
.step-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1.5px solid var(--text-5);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-4);
  flex-shrink: 0;
}
.step-item.active .step-num {
  background: var(--amber);
  color: var(--bg);
  border-color: var(--amber);
  font-weight: 700;
}
.step-item.done .step-num {
  background: #065f46;
  color: var(--green);
  border-color: #065f46;
}
.step-label {
  font-size: 13px;
  color: var(--text-3);
  line-height: 1.3;
}
.step-item.active .step-label { color: var(--text-2); font-weight: 500; }
.step-item.done .step-label  { color: var(--text-5); }

/* ── Main ── */
#main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
#content {
  flex: 1;
  overflow-y: auto;
  padding: 40px 52px;
  max-width: 800px;
}

/* ── OS picker ── */
#os-picker {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - var(--topbar-h));
  gap: 32px;
  padding: 40px;
}
#os-picker h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-1);
}
#os-picker p { color: var(--text-3); font-size: 14px; }
.os-cards {
  display: flex;
  gap: 20px;
}
.os-card {
  background: var(--surface-2);
  border: 2px solid var(--border);
  border-radius: 12px;
  padding: 28px 36px;
  cursor: pointer;
  text-align: center;
  min-width: 180px;
  transition: border-color 0.15s, background 0.15s;
}
.os-card:hover {
  border-color: var(--amber);
  background: var(--surface-3);
}
.os-card .os-icon { font-size: 40px; margin-bottom: 12px; }
.os-card h3 { font-size: 16px; color: var(--text-1); font-weight: 600; }
.os-card p  { font-size: 12px; color: var(--text-3); margin-top: 4px; }

/* ── Step content ── */
.step-tag {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--amber);
  margin-bottom: 8px;
}
.step-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 8px;
}
.step-desc {
  font-size: 14px;
  color: var(--text-3);
  line-height: 1.7;
  margin-bottom: 28px;
  max-width: 560px;
}
.instruction { margin-bottom: 20px; }
.instruction-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-4);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}
.instruction p, .instruction ol, .instruction ul {
  font-size: 14px;
  color: #cbd5e1;
  line-height: 1.7;
}
.instruction ol, .instruction ul { padding-left: 20px; }

/* Code block */
.code-block {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 20px;
  overflow: hidden;
}
.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
}
.code-lang {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-5);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.copy-btn {
  font-size: 11px;
  color: var(--amber);
  background: none;
  border: 1px solid var(--text-5);
  border-radius: 4px;
  padding: 3px 10px;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.1s;
}
.copy-btn:hover { background: var(--surface-3); }
.code-body {
  padding: 14px 16px;
  font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
  font-size: 13px;
  color: var(--code-fg);
  line-height: 1.7;
  white-space: pre;
  overflow-x: auto;
}

/* Callout */
.callout {
  background: var(--surface-3);
  border: 1px solid var(--border);
  border-left: 3px solid var(--amber);
  border-radius: 6px;
  padding: 12px 16px;
  font-size: 13px;
  color: var(--text-3);
  line-height: 1.7;
  margin-bottom: 20px;
}
.callout strong { color: var(--amber); }
.callout code {
  font-family: "SF Mono", "Fira Code", monospace;
  font-size: 12px;
  background: var(--surface-1);
  padding: 1px 5px;
  border-radius: 3px;
  color: var(--text-2);
}

/* Verify block */
.verify-block {
  background: var(--green-bg);
  border: 1px solid var(--green-bdr);
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 20px;
}
.verify-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--green);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 8px;
}
.verify-block .code-body {
  padding: 0;
  background: none;
  color: #6ee7b7;
}

/* Done state */
#done-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 16px;
  text-align: center;
}
#done-screen .done-icon { font-size: 56px; }
#done-screen h2 { font-size: 24px; font-weight: 700; color: var(--text-1); }
#done-screen p  { font-size: 14px; color: var(--text-3); max-width: 420px; line-height: 1.7; }

/* ── Footer nav ── */
#footer-nav {
  border-top: 1px solid var(--border);
  padding: 0 52px;
  height: var(--footer-h);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--surface-1);
  flex-shrink: 0;
  display: none; /* hidden until OS chosen */
}
.nav-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  font-family: inherit;
  transition: background 0.1s;
}
.btn-prev {
  background: var(--surface-3);
  color: var(--text-3);
  border: 1px solid var(--border);
}
.btn-prev:hover { background: var(--surface-2); }
.btn-next {
  background: var(--amber);
  color: var(--bg);
}
.btn-next:hover { background: var(--amber-dim); }
.btn-prev:disabled, .btn-next:disabled {
  opacity: 0.3;
  cursor: default;
}
#nav-step-info { font-size: 12px; color: var(--text-5); }
</style>
</head>
<body>

<div id="topbar">
  <div id="topbar-title">Brelly <span>/ Map Pipeline Setup</span></div>
  <div id="os-badge">
    OS: <strong id="os-label"></strong> &nbsp;·&nbsp;
    <button id="os-switch-btn">switch</button>
  </div>
</div>

<div id="body">
  <aside id="sidebar">
    <div class="sidebar-section-label">Steps</div>
    <div id="progress-wrap"><div id="progress-fill"></div></div>
    <div id="progress-label"></div>
    <ul id="step-list"></ul>
  </aside>

  <div id="main">
    <div id="content">
      <!-- OS picker shown first; replaced by step content after OS selected -->
    </div>
    <div id="footer-nav">
      <button class="nav-btn btn-prev" id="btn-prev">← <span id="prev-label"></span></button>
      <span id="nav-step-info"></span>
      <button class="nav-btn btn-next" id="btn-next"><span id="next-label"></span> →</button>
    </div>
  </div>
</div>

<script>
// Step data and app logic go here in later tasks
</script>
</body>
</html>
```

- [ ] **Step 2: Open in browser and verify layout**

Open `pipeline/setup-guide/index.html` in a browser. You should see:
- Dark background, amber title "Brelly / Map Pipeline Setup" in the top bar
- Empty main area (no sidebar, no footer yet — they are `display: none`)
- No errors in the browser console

- [ ] **Step 3: Commit**

```bash
git add pipeline/setup-guide/index.html
git commit -m "feat(setup-guide): scaffold HTML shell and CSS design system"
```

---

### Task 2: Step data array

**Files:**
- Modify: `pipeline/setup-guide/index.html` — fill in the `<script>` block with step data

Define all 11 steps as a JS array. Each step has a `title`, `desc`, and content branches `macos` / `windows` (or `shared` when identical). Each branch is an array of block objects rendered by Task 4.

Block types:
- `{ type: 'instruction', label, code, lang }` — labeled code block with Copy button
- `{ type: 'instruction', label, html }` — labeled block with arbitrary HTML (for numbered lists)
- `{ type: 'callout', html }` — amber-bordered note
- `{ type: 'verify', code }` — green verify block

- [ ] **Step 1: Replace the `<script>` placeholder with the STEPS array**

Inside `<script>`:

```js
const STEPS = [
  // ── Step 1 ──────────────────────────────────────────────────────────────
  {
    title: 'Install package manager',
    desc:  'The package manager lets you install system tools like GDAL and Python with a single command.',
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
    desc:  'Python 3.14+ is too new — GDAL binary wheels are only available for 3.10–3.12. Install 3.12 specifically.',
    macos: [
      { type: 'instruction', label: 'Run in terminal', lang: 'bash', code: `brew install python@3.12` },
      { type: 'instruction', label: 'Verify', lang: 'bash', code: `python3.12 --version` },
      { type: 'verify', code: `Python 3.12.x` },
      { type: 'callout', html: `You do not need to change your system default Python. All commands in this guide use <code>python3.12</code> explicitly.` },
    ],
    windows: [
      { type: 'instruction', label: 'Download and install', html: `<ol>
<li>Go to <a href="https://www.python.org/downloads/release/python-3128/" target="_blank" style="color:var(--amber)">python.org/downloads/release/python-3128</a></li>
<li>Download <strong>Windows installer (64-bit)</strong></li>
<li>Run the installer — <strong>check "Add python.exe to PATH"</strong> before clicking Install</li>
</ol>` },
      { type: 'instruction', label: 'Open a new PowerShell window and verify', lang: 'powershell', code: `python --version` },
      { type: 'verify', code: `Python 3.12.x` },
      { type: 'callout', html: `If you see 3.13+ or "not recognised", the PATH was not set. Re-run the installer → Modify → tick "Add Python to environment variables".` },
    ],
  },

  // ── Step 3 ──────────────────────────────────────────────────────────────
  {
    title: 'Install GDAL',
    desc:  'GDAL is the geospatial library used to read map data files. The Python bindings require it to be installed at the system level first.',
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
        code: `cd C:\\path\\to\\Brelly\npython -m venv .venv\n.venv\\Scripts\\Activate.ps1` },
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
    macos: [
      { type: 'instruction', label: 'Run in terminal (venv must be active)', lang: 'bash',
        code: `pip install -r pipeline/requirements.txt` },
      { type: 'callout', html: `If <code>gdal</code> fails, pin it to match the system GDAL:<br><br>
<code>pip install gdal==$(gdal-config --version) pyproj shapely numpy pytest</code>` },
      { type: 'instruction', label: 'Verify', lang: 'bash',
        code: `python -c "from osgeo import gdal; print(gdal.__version__)"\npython -c "import pyproj, shapely, numpy; print('OK')"` },
      { type: 'verify', code: `3.x.x\nOK` },
    ],
    windows: [
      { type: 'callout', html: `GDAL was already installed in Step 3. Install the remaining packages separately:` },
      { type: 'instruction', label: 'Run in PowerShell (venv must be active)', lang: 'powershell',
        code: `pip install pyproj shapely numpy pytest` },
      { type: 'instruction', label: 'Verify', lang: 'powershell',
        code: `python -c "from osgeo import gdal; print(gdal.__version__)"\npython -c "import pyproj, shapely, numpy; print('OK')"` },
      { type: 'verify', code: `3.x.x\nOK` },
    ],
  },

  // ── Step 6 ──────────────────────────────────────────────────────────────
  {
    title: 'Install Blender',
    desc:  'Blender bakes 3-D meshes for terrain, roads, and buildings. Without it the pipeline still runs but produces empty placeholder geometry.',
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
    macos: [
      { type: 'instruction', label: 'Run in terminal', lang: 'bash', code: `brew install meshoptimizer` },
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
<tr style="border-bottom:1px solid var(--border)"><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">center_e</td><td style="padding:6px 8px;color:var(--text-3)">LV95 easting of your map centre</td></tr>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">center_n</td><td style="padding:6px 8px;color:var(--text-3)">LV95 northing of your map centre</td></tr>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">radius_m</td><td style="padding:6px 8px;color:var(--text-3)">Half-width in metres (500 = 1 km × 1 km)</td></tr>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">base_elevation</td><td style="padding:6px 8px;color:var(--text-3)">Approximate ground elevation at centre (metres)</td></tr>
<tr><td style="padding:6px 8px;font-family:monospace;color:var(--code-fg)">source_data</td><td style="padding:6px 8px;color:var(--text-3)">Paths to alti3d.tif and swissTLM3D.gpkg</td></tr>
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
```

- [ ] **Step 2: Verify the file is valid JS — open in browser, check console for errors**

Open `pipeline/setup-guide/index.html`. Console should be error-free. Page still shows blank (no renderer yet).

- [ ] **Step 3: Commit**

```bash
git add pipeline/setup-guide/index.html
git commit -m "feat(setup-guide): add step data array (all 11 steps, both OSes)"
```

---

### Task 3: OS picker screen

**Files:**
- Modify: `pipeline/setup-guide/index.html` — add `renderOSPicker()` and `selectOS()` to `<script>`

Render the OS picker into `#content` on first load. On selection, store to `localStorage` and show the main app shell.

- [ ] **Step 1: Add state helpers and `renderOSPicker()` after the STEPS array**

```js
// ── State ────────────────────────────────────────────────────────────────
const LS_OS   = 'brelly-pipeline-os';
const LS_STEP = 'brelly-pipeline-step';
const LS_DONE = 'brelly-pipeline-done';

function getOS()       { return localStorage.getItem(LS_OS); }
function getStep()     { return parseInt(localStorage.getItem(LS_STEP) || '0', 10); }
function getDone()     { return JSON.parse(localStorage.getItem(LS_DONE) || '[]'); }
function setOS(os)     { localStorage.setItem(LS_OS, os); }
function setStep(i)    { localStorage.setItem(LS_STEP, String(i)); }
function setDone(arr)  { localStorage.setItem(LS_DONE, JSON.stringify(arr)); }
function markDone(i)   { const d = getDone(); if (!d.includes(i)) { d.push(i); setDone(d); } }

// ── OS picker ─────────────────────────────────────────────────────────────
function renderOSPicker() {
  document.getElementById('content').innerHTML = `
    <div id="os-picker">
      <h2>Choose your operating system</h2>
      <p>Commands and instructions will be tailored to your platform.</p>
      <div class="os-cards">
        <div class="os-card" onclick="selectOS('macos')">
          <div class="os-icon">🍎</div>
          <h3>macOS</h3>
          <p>Uses Homebrew</p>
        </div>
        <div class="os-card" onclick="selectOS('windows')">
          <div class="os-icon">🪟</div>
          <h3>Windows</h3>
          <p>Uses PowerShell</p>
        </div>
      </div>
    </div>`;
  document.getElementById('sidebar').style.display = 'none';
  document.getElementById('footer-nav').style.display = 'none';
  document.getElementById('os-badge').style.display = 'none';
}

function selectOS(os) {
  setOS(os);
  setStep(0);
  setDone([]);
  document.getElementById('os-label').textContent = os === 'macos' ? 'macOS' : 'Windows';
  document.getElementById('os-badge').style.display = 'flex';
  document.getElementById('sidebar').style.display = 'flex';
  document.getElementById('footer-nav').style.display = 'flex';
  renderStep(0);
}

document.getElementById('os-switch-btn').addEventListener('click', () => {
  localStorage.removeItem(LS_OS);
  renderOSPicker();
});

// ── Boot ──────────────────────────────────────────────────────────────────
if (getOS()) {
  selectOS(getOS());
} else {
  renderOSPicker();
}
```

- [ ] **Step 2: Verify in browser**

Reload. You should see the OS picker with two cards. Clicking macOS or Windows should:
- Show the OS badge in the top bar
- Show the sidebar and footer (they appear but `renderStep` is not defined yet — a console error is expected)

- [ ] **Step 3: Commit**

```bash
git add pipeline/setup-guide/index.html
git commit -m "feat(setup-guide): add OS picker screen and state helpers"
```

---

### Task 4: Step renderer

**Files:**
- Modify: `pipeline/setup-guide/index.html` — add block renderers and `renderStep()`

Render the active step into `#content` and update the sidebar.

- [ ] **Step 1: Add block renderers and `renderStep()` before the Boot section**

```js
// ── Block renderers ───────────────────────────────────────────────────────
function renderBlock(block) {
  if (block.type === 'instruction') {
    const inner = block.code
      ? `<div class="code-block">
           <div class="code-header">
             <span class="code-lang">${block.lang || 'bash'}</span>
             <button class="copy-btn" onclick="copyCode(this)">Copy</button>
           </div>
           <div class="code-body">${escHtml(block.code)}</div>
         </div>`
      : `<div class="instruction-body">${block.html}</div>`;
    return `<div class="instruction">
              <div class="instruction-label">${escHtml(block.label)}</div>
              ${inner}
            </div>`;
  }
  if (block.type === 'callout') {
    return `<div class="callout">${block.html}</div>`;
  }
  if (block.type === 'verify') {
    return `<div class="verify-block">
              <div class="verify-label">✓ Expected output</div>
              <div class="code-body">${escHtml(block.code)}</div>
            </div>`;
  }
  return '';
}

function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function copyCode(btn) {
  const code = btn.closest('.code-block').querySelector('.code-body').textContent;
  navigator.clipboard.writeText(code).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
  });
}

// ── Sidebar renderer ──────────────────────────────────────────────────────
function renderSidebar(currentIndex) {
  const done = getDone();
  const total = STEPS.length;
  const doneCount = done.length;

  document.getElementById('progress-fill').style.width = `${(doneCount / total) * 100}%`;
  document.getElementById('progress-label').textContent = `${doneCount} of ${total} complete`;

  document.getElementById('step-list').innerHTML = STEPS.map((step, i) => {
    const isDone   = done.includes(i);
    const isActive = i === currentIndex;
    const cls      = isDone ? 'done' : isActive ? 'active' : '';
    const num      = isDone ? '✓' : i + 1;
    return `<li class="step-item ${cls}" onclick="goToStep(${i})">
              <div class="step-num">${num}</div>
              <div class="step-label">${escHtml(step.title)}</div>
            </li>`;
  }).join('');
}

// ── Step renderer ─────────────────────────────────────────────────────────
function renderStep(index) {
  setStep(index);
  const os   = getOS();
  const step = STEPS[index];

  // Collect blocks: shared first (if before), then OS-specific, then shared (if after)
  // Convention: shared blocks in step.shared render after OS-specific ones,
  // except steps where macos/windows arrays are empty (step 8) — then only shared.
  let blocks = [];
  const osBlocks     = (step[os] || []);
  const sharedBlocks = (step.shared || []);
  if (osBlocks.length === 0 && sharedBlocks.length > 0) {
    blocks = sharedBlocks;
  } else {
    blocks = [...osBlocks, ...sharedBlocks];
  }

  const blocksHtml = blocks.map(renderBlock).join('');

  document.getElementById('content').innerHTML = `
    <div class="step-tag">Step ${index + 1} of ${STEPS.length}</div>
    <div class="step-title">${escHtml(step.title)}</div>
    <div class="step-desc">${escHtml(step.desc)}</div>
    ${blocksHtml}`;

  renderSidebar(index);
  renderFooter(index);
  document.getElementById('content').scrollTop = 0;
}

// ── Footer renderer ───────────────────────────────────────────────────────
function renderFooter(index) {
  const prev = document.getElementById('btn-prev');
  const next = document.getElementById('btn-next');
  const info = document.getElementById('nav-step-info');

  info.textContent = `Step ${index + 1} of ${STEPS.length}`;

  if (index === 0) {
    prev.style.visibility = 'hidden';
  } else {
    prev.style.visibility = 'visible';
    document.getElementById('prev-label').textContent = STEPS[index - 1].title;
  }

  if (index === STEPS.length - 1) {
    document.getElementById('next-label').textContent = 'Finish';
  } else {
    document.getElementById('next-label').textContent = STEPS[index + 1].title;
  }
}

function goToStep(index) {
  renderStep(index);
}

// ── Navigation ────────────────────────────────────────────────────────────
document.getElementById('btn-prev').addEventListener('click', () => {
  const i = getStep();
  if (i > 0) renderStep(i - 1);
});

document.getElementById('btn-next').addEventListener('click', () => {
  const i = getStep();
  markDone(i);
  if (i < STEPS.length - 1) {
    renderStep(i + 1);
  } else {
    markDone(i);
    renderDone();
  }
});

// ── Done screen ───────────────────────────────────────────────────────────
function renderDone() {
  renderSidebar(STEPS.length); // all done
  document.getElementById('content').innerHTML = `
    <div id="done-screen">
      <div class="done-icon">🏁</div>
      <h2>You're all set!</h2>
      <p>The pipeline is installed and ready. Run it against any map config and the output will land in <code>maps/&lt;name&gt;/</code>.</p>
    </div>`;
  document.getElementById('btn-next').style.display = 'none';
  document.getElementById('btn-prev').style.visibility = 'visible';
  document.getElementById('prev-label').textContent = STEPS[STEPS.length - 1].title;
  document.getElementById('nav-step-info').textContent = 'Complete';
}
```

- [ ] **Step 2: Verify in browser — go through all 11 steps on both OSes**

Check:
- Each step renders title, description, and all blocks
- Sidebar highlights the active step and shows ✓ for completed ones
- Progress bar advances as steps are completed
- Prev/Next navigate correctly
- Step 1 hides the Prev button
- Last step's Next button says "Finish" and shows the done screen
- "switch" link in top bar returns to OS picker and clears progress
- Reloading the page restores the last OS and step (localStorage)

- [ ] **Step 3: Commit**

```bash
git add pipeline/setup-guide/index.html
git commit -m "feat(setup-guide): add step renderer, sidebar, footer nav, done screen"
```

---

### Task 5: Copy button + final polish

**Files:**
- Modify: `pipeline/setup-guide/index.html` — verify copy button works; fix any visual issues found during step 2 review

- [ ] **Step 1: Test copy button on each code block type**

Open the page, navigate to Step 1 (macOS). Click Copy on the Homebrew install command. Paste into a text editor — verify the full command was copied with no extra whitespace or HTML artifacts.

Repeat on Step 4 (multi-line code block) and Step 9 (Windows tab, copy the PowerShell command).

- [ ] **Step 2: Verify optional step (Step 7 — gltfpack)**

Navigate to Step 7. Confirm content renders for both OSes. Click Next — it should mark Step 7 done and advance to Step 8.

- [ ] **Step 3: Verify shared-only step (Step 8 — download data)**

Navigate to Step 8. Switch between macOS and Windows via "switch" link (which resets to picker). Confirm the step content is identical on both OSes (no duplication, just shared blocks).

- [ ] **Step 4: Commit**

```bash
git add pipeline/setup-guide/index.html
git commit -m "feat(setup-guide): verified copy button and all step variants"
```

---

### Task 6: Wire into pipeline docs

**Files:**
- Modify: `pipeline/SETUP_MACOS.md`
- Modify: `pipeline/SETUP_WINDOWS.md`
- Modify: `pipeline/README.md`

Add a prominent link to the interactive guide at the top of each setup doc and the README.

- [ ] **Step 1: Add link to SETUP_MACOS.md**

After the title line, add:

```markdown
> **Prefer a visual guide?** Open [`pipeline/setup-guide/index.html`](setup-guide/index.html) in your browser for an interactive step-by-step walkthrough.
```

- [ ] **Step 2: Add link to SETUP_WINDOWS.md**

Same line, same position.

- [ ] **Step 3: Update README.md**

Change the first-time line to:

```markdown
> **First time?** Try the [interactive setup guide](setup-guide/index.html) (open in browser) or read the text guides: [macOS](SETUP_MACOS.md) · [Windows](SETUP_WINDOWS.md)
```

- [ ] **Step 4: Commit**

```bash
git add pipeline/SETUP_MACOS.md pipeline/SETUP_WINDOWS.md pipeline/README.md
git commit -m "docs: link interactive setup guide from README and setup docs"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Covered by |
|-----------------|-----------|
| Single HTML file, no build step | Task 1 scaffold |
| OS picker on first load | Task 3 |
| OS stored in localStorage | Task 3 state helpers |
| Sticky OS badge + switch link | Task 3 `selectOS()` + switch listener |
| Sidebar with progress bar + step list | Task 4 `renderSidebar()` |
| Active/done step states in sidebar | Task 4 CSS classes |
| Sidebar click navigates to step | Task 4 `goToStep()` |
| Step content: tag, title, desc, blocks | Task 4 `renderStep()` |
| Instruction blocks with code + Copy | Task 4 `renderBlock()` |
| Callout notes | Task 4 `renderBlock()` |
| Verify blocks | Task 4 `renderBlock()` |
| Prev/Next footer nav | Task 4 `renderFooter()` + listeners |
| Step marked done on Next | Task 4 `markDone()` |
| Progress persists across reload | Task 3 localStorage + boot logic |
| Done screen on finishing | Task 4 `renderDone()` |
| Copy button with Copied! feedback | Task 4 `copyCode()` |
| All 11 steps, both OSes | Task 2 STEPS array |
| Links from docs | Task 6 |

**Placeholder scan:** None found.

**Type consistency:** `renderStep(index)`, `goToStep(index)`, `markDone(i)`, `getStep()` — all consistent. `renderBlock(block)` receives objects from STEPS array — shape matches all block type renderers.
