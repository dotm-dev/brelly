// ── State ─────────────────────────────────────────────────────────────────
const LS_OS   = 'brelly-pipeline-os';
const LS_STEP = 'brelly-pipeline-step';
const LS_DONE = 'brelly-pipeline-done';

function getOS()      { return localStorage.getItem(LS_OS); }
function getStep()    { const n = parseInt(localStorage.getItem(LS_STEP) || '0', 10); return isNaN(n) ? 0 : Math.min(Math.max(0, n), STEPS.length - 1); }
function getDone()    { try { return JSON.parse(localStorage.getItem(LS_DONE) || '[]'); } catch { return []; } }
function setOS(os)    { localStorage.setItem(LS_OS, os); }
function setStep(i)   { localStorage.setItem(LS_STEP, String(i)); }
function setDone(arr) { localStorage.setItem(LS_DONE, JSON.stringify(arr)); }
function markDone(i)  { const d = getDone(); if (!d.includes(i)) { d.push(i); setDone(d); } }
function unmarkDone(i){ setDone(getDone().filter(n => n !== i)); }

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
  if (block.type === 'instruction') {
    const inner = block.code
      ? `<div class="code-block">
           <div class="code-header">
             <span class="code-lang">${block.lang || 'bash'}</span>
             <button class="copy-btn" onclick="copyCode(this)">Copy</button>
           </div>
           <div class="code-body">${escHtml(block.code)}</div>
         </div>`
      // trusted author HTML — block.html is a static string literal in STEPS, never from external input
      : `<div class="instruction-body">${block.html}</div>`;
    return `<div class="instruction">
              <div class="instruction-label">${escHtml(block.label)}</div>
              ${inner}
            </div>`;
  }
  if (block.type === 'callout') {
    // trusted author HTML — block.html is a static string literal in STEPS, never from external input
    return `<div class="callout">${block.html}</div>`;
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
              <div class="code-body">${escHtml(block.code)}</div>
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
