// ── State ─────────────────────────────────────────────────────────────────
const LS_OS   = 'brelly-pipeline-os';
const LS_STEP = 'brelly-pipeline-step';
const LS_DONE = 'brelly-pipeline-done';
const LS_AREA = 'brelly-pipeline-area';

function getOS()      { return localStorage.getItem(LS_OS); }
function getStep()    { const n = parseInt(localStorage.getItem(LS_STEP) || '0', 10); return isNaN(n) ? 0 : Math.min(Math.max(0, n), STEPS.length - 1); }
function getDone()    { try { return JSON.parse(localStorage.getItem(LS_DONE) || '[]'); } catch { return []; } }
function getArea()    { const v = localStorage.getItem(LS_AREA); return v !== null ? v : ''; }
function setOS(os)    { localStorage.setItem(LS_OS, os); }
function setStep(i)   { localStorage.setItem(LS_STEP, String(i)); }
function setDone(arr) { localStorage.setItem(LS_DONE, JSON.stringify(arr)); }
function markDone(i)  { const d = getDone(); if (!d.includes(i)) { d.push(i); setDone(d); } }
function unmarkDone(i){ setDone(getDone().filter(n => n !== i)); }

function onAreaInput(el) {
  const raw = el.value;
  const start = el.selectionStart;
  const filtered = raw.replace(/[^a-zA-Z0-9_-]/g, '');
  if (filtered !== raw) {
    const removedBefore = raw.slice(0, start).replace(/[a-zA-Z0-9_-]/g, '').length;
    el.value = filtered;
    const pos = start - removedBefore;
    el.setSelectionRange(pos, pos);
  }
  localStorage.setItem(LS_AREA, filtered);
  refreshAreaInPage();
}

function prettifyAreaName(name) {
  return name.replace(/[_-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function applyAreaInspect() {
  const text = document.getElementById('area-inspect-output').value.trim();
  const map  = Object.fromEntries(
    text.split('\n').map(l => l.trim().split('=')).filter(p => p.length === 2)
  );
  if (map.CENTER_E)       document.getElementById('cfg-e').value    = map.CENTER_E;
  if (map.CENTER_N)       document.getElementById('cfg-n').value    = map.CENTER_N;
  if (map.BASE_ELEVATION) document.getElementById('cfg-elev').value = map.BASE_ELEVATION;
  // auto-suggest displayName if still empty
  const disp = document.getElementById('cfg-display');
  if (!disp.value.trim()) disp.value = prettifyAreaName(getArea() || 'my_area');
}

function downloadConfig() {
  const name        = (getArea() || 'my_area').replace(/[^a-zA-Z0-9_-]/g, '_');
  const displayName =  document.getElementById('cfg-display').value.trim() || prettifyAreaName(name);
  const center_e    = parseFloat(document.getElementById('cfg-e').value)    || 0;
  const center_n    = parseFloat(document.getElementById('cfg-n').value)    || 0;
  const radius_m    = parseFloat(document.getElementById('cfg-radius').value) || 500;
  const base_elev   = parseFloat(document.getElementById('cfg-elev').value)   || 0;

  const config = {
    name, displayName, center_e, center_n, radius_m,
    base_elevation: base_elev,
    start_line:    { position: { x: 0, y: 0, z: -50  }, normal: { x: 0, y: 0, z: 1 }, widthMetres: 12 },
    finish_line:   { position: { x: 0, y: 0, z:  200 }, normal: { x: 0, y: 0, z: 1 }, widthMetres: 12 },
    spawn_position: { x: 0, y: 1, z: -45 },
    spawn_rotation: { x: 0, y: 0, z: 0, w: 1 },
    checkpoints: [],
    source_data: {
      dem: `data/${name}/alti3d.vrt`,
      tlm: `data/${name}/swissTLM3D.gpkg`,
    },
  };

  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' }));
  a.download = `${name}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function downloadRunScript() {
  const area = getArea() || 'my_area';
  const os   = getOS();
  let content, filename;
  if (os === 'windows') {
    content  = `Set-Location $PSScriptRoot\n.venv\\Scripts\\Activate.ps1\npython pipeline\\run_pipeline.py "pipeline\\config\\${area}.json"\n`;
    filename = `run_${area}.ps1`;
  } else {
    content  = `#!/usr/bin/env bash\nset -e\ncd "$(dirname "$0")"\nsource .venv/bin/activate\npython pipeline/run_pipeline.py "pipeline/config/${area}.json"\n`;
    filename = `run_${area}.sh`;
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([content], { type: 'text/plain' }));
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function refreshAreaInPage() {
  document.querySelectorAll('[data-area-template]').forEach(el => {
    el.textContent = subArea(el.dataset.areaTemplate);
  });
  document.querySelectorAll('[data-area-template-html]').forEach(el => {
    el.innerHTML = subArea(el.dataset.areaTemplateHtml);
  });
}

function subArea(str) { return str.replace(/\{AREA\}/g, getArea() || 'my_area'); }

// ── OS picker ─────────────────────────────────────────────────────────────
function renderOSPicker() {
  document.getElementById('content-inner').innerHTML = `
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
  document.getElementById('sidebar').style.display    = 'none';
  document.getElementById('footer-nav').style.display = 'none';
  document.getElementById('os-badge').style.display   = 'none';
}

function selectOS(os) {
  setOS(os); setStep(0); setDone([]);
  document.getElementById('os-label').textContent     = os === 'macos' ? 'macOS' : 'Windows';
  document.getElementById('os-badge').style.display   = 'flex';
  document.getElementById('sidebar').style.display    = 'flex';
  document.getElementById('footer-nav').style.display = 'flex';
  renderStep(0);
}

document.getElementById('os-switch-btn').addEventListener('click', () => {
  localStorage.removeItem(LS_OS);
  renderOSPicker();
});

// ── Block renderers ───────────────────────────────────────────────────────
function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderBlock(block) {
  if (block.type === 'area-input') {
    return `<div class="instruction">
              <div class="instruction-label">Area name</div>
              <input id="area-name-input" type="text" class="area-name-input"
                placeholder="e.g. new_york"
                value="${escHtml(getArea())}"
                oninput="onAreaInput(this)" />
              <div style="font-size:12px;color:var(--text-4);margin-top:8px">
                Used in folder paths and config filenames across all following steps —
                updates live as you type. Letters, numbers, hyphens, underscores only.
              </div>
            </div>`;
  }
  if (block.type === 'instruction') {
    const inner = block.code
      ? `<div class="code-block">
           <div class="code-header">
             <span class="code-lang">${block.lang || 'bash'}</span>
             <button class="copy-btn" onclick="copyCode(this)">Copy</button>
           </div>
           <div class="code-body" data-area-template="${escHtml(block.code)}">${escHtml(subArea(block.code))}</div>
         </div>`
      // trusted author HTML — block.html is a static string literal in STEPS, never from external input
      : `<div class="instruction-body" data-area-template-html="${escHtml(block.html)}">${subArea(block.html)}</div>`;
    return `<div class="instruction">
              <div class="instruction-label">${escHtml(block.label)}</div>
              ${inner}
            </div>`;
  }
  if (block.type === 'callout') {
    // trusted author HTML — block.html is a static string literal in STEPS, never from external input
    return `<div class="callout" data-area-template-html="${escHtml(block.html)}">${subArea(block.html)}</div>`;
  }
  if (block.type === 'config-builder') {
    const area = getArea() || 'my_area';
    const os   = getOS();
    const cmd  = os === 'windows'
      ? `python pipeline\\inspect_area.py data\\{AREA}\\alti3d.vrt`
      : `python pipeline/inspect_area.py data/{AREA}/alti3d.vrt`;
    const compactRow = (id, label, type, placeholder) =>
      `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
        <span style="font-size:11px;font-family:monospace;color:var(--code-fg);width:130px;text-align:right;flex-shrink:0">${label}</span>
        <input id="${id}" type="${type}" class="config-input" style="max-width:200px" placeholder="${placeholder}" />
      </div>`;
    return `
      <div class="instruction" style="margin-bottom:20px">
        <div class="instruction-label">1 — Extract coordinates from your data (venv active)</div>
        <div class="code-block" style="margin-bottom:12px">
          <div class="code-header">
            <span class="code-lang">${os === 'windows' ? 'powershell' : 'bash'}</span>
            <button class="copy-btn" onclick="copyCode(this)">Copy</button>
          </div>
          <div class="code-body" data-area-template="${escHtml(cmd)}">${escHtml(subArea(cmd))}</div>
        </div>
        <textarea id="area-inspect-output" class="checker-textarea" style="height:80px"
          placeholder="CENTER_E=2683000&#10;CENTER_N=1247500&#10;BASE_ELEVATION=450.0" spellcheck="false"
          onpaste="setTimeout(applyAreaInspect, 0)"></textarea>
      </div>

      <div class="instruction" style="margin-bottom:20px">
        <div class="instruction-label">2 — Name your map</div>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
          <span style="font-size:11px;font-family:monospace;color:var(--code-fg);width:130px;text-align:right;flex-shrink:0">displayName</span>
          <input id="cfg-display" type="text" class="config-input" style="max-width:260px"
            placeholder="${escHtml(prettifyAreaName(area))}" />
        </div>
        <div style="display:flex;align-items:center;gap:10px">
          <span style="font-size:11px;font-family:monospace;color:var(--code-fg);width:130px;text-align:right;flex-shrink:0">radius_m</span>
          <input id="cfg-radius" type="number" class="config-input" style="max-width:120px" value="500" />
          <span style="font-size:12px;color:var(--text-4)">metres — how large you want the race area<br><span style="font-size:11px;color:var(--text-5)">250 = tight circuit &nbsp;·&nbsp; 500 = 1 km² &nbsp;·&nbsp; 1000 = 4 km²</span></span>
        </div>
      </div>

      <details style="margin-bottom:20px;border:1px solid var(--border);border-radius:8px;overflow:hidden">
        <summary style="padding:10px 16px;cursor:pointer;font-size:12px;font-weight:600;color:var(--text-4);text-transform:uppercase;letter-spacing:0.06em;background:var(--surface-2);list-style:none;user-select:none">
          Override extracted coordinates
        </summary>
        <div style="padding:16px;background:var(--surface-1)">
          ${compactRow('cfg-e',    'center_e',      'number', 'auto-filled')}
          ${compactRow('cfg-n',    'center_n',      'number', 'auto-filled')}
          ${compactRow('cfg-elev', 'base_elevation','number', 'auto-filled')}
        </div>
      </details>

      <button class="apply-btn" onclick="downloadConfig()">
        ↓ Download <span data-area-template="{AREA}.json">${escHtml(subArea('{AREA}.json'))}</span>
      </button>
      <div class="config-hint" style="margin-top:10px">
        Save to <code style="font-size:11px">pipeline/config/</code> in your Brelly folder.
        Race layout uses sensible defaults — edit the JSON directly to adjust.
      </div>`;
  }
  if (block.type === 'run-script') {
    const os = getOS();
    const isWin = os === 'windows';
    const ext = isWin ? 'ps1' : 'sh';
    const lang = isWin ? 'powershell' : 'bash';
    const tpl = isWin
      ? `Set-Location $PSScriptRoot\n.venv\\Scripts\\Activate.ps1\npython pipeline\\run_pipeline.py "pipeline\\config\\{AREA}.json"`
      : `#!/usr/bin/env bash\nset -e\ncd "$(dirname "$0")"\nsource .venv/bin/activate\npython pipeline/run_pipeline.py "pipeline/config/{AREA}.json"`;
    return `<div class="instruction">
              <div class="instruction-label">Download run script</div>
              <div class="code-block" style="margin-bottom:14px">
                <div class="code-header">
                  <span class="code-lang">${lang}</span>
                </div>
                <div class="code-body" data-area-template="${escHtml(tpl)}">${escHtml(subArea(tpl))}</div>
              </div>
              <button class="apply-btn" onclick="downloadRunScript()">
                ↓ <span data-area-template="run_{AREA}.${ext}">${escHtml(subArea(`run_{AREA}.${ext}`))}</span>
              </button>
              <div style="font-size:12px;color:var(--text-4);margin-top:10px">
                Place the script in your Brelly project folder and run it from there —
                it activates the virtual environment and runs the pipeline in one step.
              </div>
            </div>`;
  }
  if (block.type === 'checker-input') {
    return `<div class="checker-input">
              <div class="instruction-label">Paste the output here</div>
              <textarea id="checker-output" class="checker-textarea"
                placeholder="HOMEBREW=ok&#10;PYTHON312=missing&#10;GDAL_SYS=ok&#10;..." spellcheck="false"></textarea>
              <button class="apply-btn" onclick="applyCheckerOutput()">Apply &amp; jump to first incomplete step →</button>
            </div>`;
  }
  if (block.type === 'verify') {
    return `<div class="verify-block">
              <div class="verify-label">✓ Expected output</div>
              <div class="code-body" data-area-template="${escHtml(block.code)}">${escHtml(subArea(block.code))}</div>
            </div>`;
  }
  return '';
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
  const done      = getDone();
  const doneCount = done.length;

  document.getElementById('progress-fill').style.width = `${(doneCount / STEPS.length) * 100}%`;
  document.getElementById('progress-label').textContent = `${doneCount} of ${STEPS.length} complete`;

  document.getElementById('step-list').innerHTML = STEPS.map((step, i) => {
    const isDone   = done.includes(i);
    const isActive = i === currentIndex;
    const cls      = isActive ? (isDone ? 'done active' : 'active') : (isDone ? 'done' : '');
    const num      = isDone ? '✓' : i + 1;
    return `<li class="step-item ${cls}" onclick="goToStep(${i})">
              <div class="step-num">${num}</div>
              <div class="step-label">${escHtml(step.title)}</div>
            </li>`;
  }).join('');
}

// ── Precheck renderer ─────────────────────────────────────────────────────
function renderPrecheck(step, os) {
  const pc = step.precheck;
  if (!pc) return '';
  const check = pc.macos !== undefined ? pc[os] : pc; // OS-specific or shared
  if (!check) return '';
  const lang = check.lang === 'powershell' ? 'powershell' : 'bash';
  return `<details class="precheck">
    <summary>Already have this installed? Check first</summary>
    <div class="precheck-body">
      <div class="code-block">
        <div class="code-header">
          <span class="code-lang">${lang}</span>
          <button class="copy-btn" onclick="copyCode(this)">Copy</button>
        </div>
        <div class="code-body" data-area-template="${escHtml(check.code)}">${escHtml(subArea(check.code))}</div>
      </div>
      <div class="verify-block">
        <div class="verify-label">✓ If already done, you should see</div>
        <div class="code-body" data-area-template="${escHtml(check.verify)}">${escHtml(subArea(check.verify))}</div>
      </div>
    </div>
  </details>`;
}

// ── Step renderer ─────────────────────────────────────────────────────────
function renderStep(i) {
  setStep(i);
  const step = STEPS[i];
  const os   = getOS();

  const osBlocks     = step[os] || [];
  const sharedBlocks = step.shared || [];
  const blocks = (osBlocks.length === 0 && sharedBlocks.length > 0)
    ? sharedBlocks
    : [...osBlocks, ...sharedBlocks];

  document.getElementById('content-inner').innerHTML = `
    <div class="step-tag">Step ${i + 1} of ${STEPS.length}</div>
    <div class="step-title">${escHtml(step.title)}</div>
    <div class="step-desc">${escHtml(step.desc)}</div>
    ${renderPrecheck(step, os)}
    ${blocks.map(renderBlock).join('')}`;

  renderSidebar(i);
  renderFooter(i);
  document.getElementById('content').scrollTop = 0;
}

// ── Footer renderer ───────────────────────────────────────────────────────
function renderFooter(index) {
  document.getElementById('nav-step-info').textContent = `Step ${index + 1} of ${STEPS.length}`;
  document.getElementById('btn-prev').style.visibility = index === 0 ? 'hidden' : 'visible';
  if (index > 0) {
    document.getElementById('prev-label').textContent = STEPS[index - 1].title;
  }
  document.getElementById('next-label').textContent =
    index === STEPS.length - 1 ? 'Finish' : STEPS[index + 1].title;
  document.getElementById('btn-next').style.display = '';
}

function goToStep(index) { renderStep(index); }

// ── Navigation ────────────────────────────────────────────────────────────
document.getElementById('btn-prev').addEventListener('click', () => {
  const i = getStep();
  if (i > 0) { unmarkDone(i - 1); renderStep(i - 1); }
});

document.getElementById('btn-next').addEventListener('click', () => {
  const i = getStep();
  markDone(i);
  if (i < STEPS.length - 1) { renderStep(i + 1); } else { renderDone(); }
});

// ── Done screen ───────────────────────────────────────────────────────────
function renderDone() {
  markDone(STEPS.length - 1);
  renderSidebar(STEPS.length);
  document.getElementById('content-inner').innerHTML = `
    <div id="done-screen">
      <div class="done-icon">🏁</div>
      <h2>You're all set!</h2>
      <p>The pipeline is installed and ready. Run it against any map config and the output will land in <code>maps/&lt;name&gt;/</code>.</p>
    </div>`;
  document.getElementById('btn-next').style.display        = 'none';
  document.getElementById('btn-prev').style.visibility     = 'visible';
  document.getElementById('prev-label').textContent        = STEPS[STEPS.length - 1].title;
  document.getElementById('nav-step-info').textContent     = 'Complete ✓';
}

// ── Checker ───────────────────────────────────────────────────────────────
// Step index mapping: STEPS[0]=checker, STEPS[1]=pkg-mgr, STEPS[2]=python, ...
const CHECKER_MAP = {
  macos:   { HOMEBREW: 1, PYTHON312: 2, GDAL_SYS: 3, VENV: 4, DEPS: 5, BLENDER: 6, GLTFPACK: 7 },
  windows: {              PYTHON312: 2, GDAL_PY:  3, VENV: 4, DEPS: 5, BLENDER: 6, GLTFPACK: 7 },
};

function applyCheckerOutput() {
  const text = document.getElementById('checker-output').value.trim();
  if (!text) return;

  const os = getOS();
  const results = Object.fromEntries(
    text.split('\n').map(l => l.trim().split('=')).filter(p => p.length === 2)
  );

  const done = new Set([0]); // step 0 (this step) is done

  // On Windows step 1 (package manager) is a no-op — always satisfied
  if (os === 'windows') done.add(1);

  const map = CHECKER_MAP[os] || {};
  for (const [key, stepIndex] of Object.entries(map)) {
    if (results[key] === 'ok') done.add(stepIndex);
  }
  // Step 8 (source data) needs both files
  if (results.DATA_DEM === 'ok' && results.DATA_TLM === 'ok') done.add(8);
  // Step 9 (config)
  if (results.CONFIG === 'ok') done.add(9);

  setDone([...done]);

  const first = [...Array(STEPS.length).keys()].find(i => !done.has(i)) ?? STEPS.length - 1;
  renderStep(first);
}

// ── Boot ──────────────────────────────────────────────────────────────────
function restoreSession(os) {
  document.getElementById('os-label').textContent     = os === 'macos' ? 'macOS' : 'Windows';
  document.getElementById('os-badge').style.display   = 'flex';
  document.getElementById('sidebar').style.display    = 'flex';
  document.getElementById('footer-nav').style.display = 'flex';
  if (getDone().length === STEPS.length) { renderDone(); } else { renderStep(getStep()); }
}

if (getOS()) { restoreSession(getOS()); } else { renderOSPicker(); }
