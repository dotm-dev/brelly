#!/usr/bin/env bash
# pipeline/setup.sh
# One-command installer: checks each Brelly pipeline requirement and
# installs what's missing (no per-step prompts by default), then launches
# the app. Run from anywhere:
#   bash pipeline/setup.sh
#   bash pipeline/setup.sh --verbose      # stream full installer output
#   bash pipeline/setup.sh --interactive  # confirm before each install
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

VERBOSE=0
INTERACTIVE=0
for arg in "$@"; do
  case "$arg" in
    -v|--verbose) VERBOSE=1 ;;
    -i|--interactive) INTERACTIVE=1 ;;
  esac
done

# Homebrew's installer never edits shell profiles for you — it just prints
# instructions to do so. Without that edit, every new shell (including a
# restarted run of this script) starts with a PATH that doesn't see brew,
# even though it's installed on disk. Bootstrap it here unconditionally.
if ! command -v brew >/dev/null 2>&1; then
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
fi

confirm() {
  local prompt="$1"
  if [ "$INTERACTIVE" -eq 0 ]; then
    return 0
  fi
  read -r -p "$prompt [y/N] " reply
  case "$reply" in
    [yY][eE][sS]|[yY]) return 0 ;;
    *) return 1 ;;
  esac
}

# Colored status lines. Only used when stdout is a real terminal, so piped
# output/log files don't get raw escape codes.
if [ -t 1 ]; then
  C_GREEN=$'\033[0;32m'
  C_RED=$'\033[0;31m'
  C_CYAN=$'\033[0;36m'
  C_RESET=$'\033[0m'
else
  C_GREEN=''
  C_RED=''
  C_CYAN=''
  C_RESET=''
fi

ok() {
  echo "${C_GREEN}✓ $1${C_RESET}"
}

missing() {
  echo "${C_RED}✗ $1${C_RESET}"
}

will_run() {
  echo "${C_CYAN}  Will run: $1${C_RESET}"
}

step_failed() {
  echo ""
  missing "$1"
  echo "  Run this manually, then re-run: bash pipeline/setup.sh"
  exit 1
}

# Runs a non-interactive install command. In verbose mode, streams its
# output live. Otherwise shows a spinner with elapsed time and only prints
# the captured output if the command fails — install steps here (brew/npm/
# pip) don't prompt for input, so it's safe to hide their noise.
run_step() {
  local desc="$1"; shift
  if [ "$VERBOSE" -eq 1 ]; then
    "$@"
    return $?
  fi

  local log
  log="$(mktemp)"
  "$@" >"$log" 2>&1 &
  local pid=$!
  local spin='|/-\'
  local i=0
  local start=$SECONDS
  while kill -0 "$pid" 2>/dev/null; do
    i=$(( (i + 1) % 4 ))
    printf "\r  %s... %s (%ds)" "$desc" "${spin:$i:1}" "$(( SECONDS - start ))"
    sleep 0.2
  done
  wait "$pid"
  local status=$?
  local elapsed=$(( SECONDS - start ))
  if [ "$status" -eq 0 ]; then
    printf "\r  %s... done (%ds)\n" "$desc" "$elapsed"
  else
    printf "\r  %s... failed (%ds)\n" "$desc" "$elapsed"
    cat "$log"
  fi
  rm -f "$log"
  return "$status"
}

echo "Brelly pipeline setup"
echo "======================"

# 1. Homebrew
# Not wrapped in run_step, and deliberately NOT run with NONINTERACTIVE=1:
# that env var doesn't just skip the installer's "Press RETURN to continue"
# prompt, it also switches its sudo check to `sudo -n` (non-interactive,
# no password prompt allowed) — which fails outright if you don't already
# have a cached sudo credential, even on a genuine admin account. Left as
# the installer's normal interactive flow so it can actually prompt for
# your admin password when needed.
if ! command -v brew >/dev/null 2>&1; then
  echo ""
  missing "Homebrew not found."
  will_run "/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  if confirm "Proceed?"; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # The installer doesn't update PATH for the current shell, only future
    # ones (via shell profile edits it prints instructions for) — so pick up
    # the freshly installed brew here, checking both install locations.
    if [ -x /opt/homebrew/bin/brew ]; then
      eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
      eval "$(/usr/local/bin/brew shellenv)"
    fi
  else
    step_failed "Homebrew is required. Install it from https://brew.sh"
  fi
fi
command -v brew >/dev/null 2>&1 || step_failed "Homebrew still not found after install attempt."
ok "Homebrew"

# 2. Python 3.12
if ! command -v python3.12 >/dev/null 2>&1; then
  echo ""
  missing "Python 3.12 not found."
  will_run "brew install python@3.12"
  if confirm "Proceed?"; then
    run_step "Installing Python 3.12" brew install python@3.12 || step_failed "brew install python@3.12 failed."
  else
    step_failed "Python 3.12 is required."
  fi
fi
command -v python3.12 >/dev/null 2>&1 || step_failed "Python 3.12 still not found after install attempt."
ok "Python 3.12"

# 2b. tkinter (app.py's GUI toolkit; Homebrew's python@3.12 doesn't bundle Tk)
if ! python3.12 -c "import tkinter" >/dev/null 2>&1; then
  echo ""
  missing "tkinter not found."
  will_run "brew install python-tk@3.12"
  if confirm "Proceed?"; then
    run_step "Installing tkinter" brew install python-tk@3.12 || step_failed "brew install python-tk@3.12 failed."
  else
    step_failed "tkinter is required to launch the pipeline app."
  fi
fi
python3.12 -c "import tkinter" >/dev/null 2>&1 || step_failed "tkinter still not importable after install attempt."
ok "tkinter"

# 3. GDAL system library
if ! command -v gdal-config >/dev/null 2>&1; then
  echo ""
  missing "GDAL system library not found."
  will_run "brew install gdal"
  if confirm "Proceed?"; then
    run_step "Installing GDAL" brew install gdal || step_failed "brew install gdal failed."
  else
    step_failed "GDAL is required."
  fi
fi
command -v gdal-config >/dev/null 2>&1 || step_failed "GDAL still not found after install attempt."
ok "GDAL system library"

# 4. Blender
if ! command -v blender >/dev/null 2>&1; then
  echo ""
  missing "Blender not found."
  will_run "brew install --cask blender"
  if confirm "Proceed?"; then
    run_step "Installing Blender" brew install --cask blender || step_failed "brew install --cask blender failed."
  else
    step_failed "Blender is required."
  fi
fi
command -v blender >/dev/null 2>&1 || step_failed "Blender still not found after install attempt."
ok "Blender"

# 5. Node.js (needed to install gltfpack, which ships as an npm package —
# there's no Homebrew formula for it)
if ! command -v npm >/dev/null 2>&1; then
  echo ""
  missing "Node.js not found."
  will_run "brew install node"
  if confirm "Proceed?"; then
    run_step "Installing Node.js" brew install node || step_failed "brew install node failed."
  else
    step_failed "Node.js is required to install gltfpack."
  fi
fi
command -v npm >/dev/null 2>&1 || step_failed "Node.js still not found after install attempt."
ok "Node.js"

# 6. gltfpack (published on npm with prebuilt binaries; no Homebrew formula)
if ! command -v gltfpack >/dev/null 2>&1; then
  echo ""
  missing "gltfpack not found."
  will_run "npm install -g gltfpack"
  if confirm "Proceed?"; then
    run_step "Installing gltfpack" npm install -g gltfpack || step_failed "npm install -g gltfpack failed. Download manually from https://github.com/zeux/meshoptimizer/releases"
  else
    step_failed "gltfpack is required. Download manually from https://github.com/zeux/meshoptimizer/releases"
  fi
fi
command -v gltfpack >/dev/null 2>&1 || step_failed "gltfpack still not found after install attempt."
ok "gltfpack"

# 7. Virtual environment
if [ ! -f ".venv/bin/python3" ]; then
  echo ""
  missing "Virtual environment not found."
  will_run "python3.12 -m venv .venv"
  if confirm "Proceed?"; then
    run_step "Creating virtual environment" python3.12 -m venv .venv || step_failed "python3.12 -m venv .venv failed."
  else
    step_failed "A virtual environment is required."
  fi
fi
[ -f ".venv/bin/python3" ] || step_failed "Virtual environment still missing after creation attempt."
ok "Virtual environment"

# 8. Python dependencies
if ! .venv/bin/python3 -c "from osgeo import gdal; import pyproj, shapely, numpy" >/dev/null 2>&1; then
  echo ""
  missing "Python dependencies not installed."
  will_run ".venv/bin/pip install -r pipeline/requirements.txt"
  if confirm "Proceed?"; then
    run_step "Installing Python dependencies" .venv/bin/pip install -r pipeline/requirements.txt || step_failed ".venv/bin/pip install -r pipeline/requirements.txt failed."
  else
    step_failed "Python dependencies are required."
  fi
fi
.venv/bin/python3 -c "from osgeo import gdal; import pyproj, shapely, numpy" >/dev/null 2>&1 || step_failed "Dependencies still not importable after install attempt."
ok "Python dependencies"

# 9. Launch the app
echo ""
echo "All requirements satisfied. Launching Brelly Pipeline app..."
echo "Next time, skip these checks and launch the app directly with:"
echo "  .venv/bin/python3 pipeline/app.py"
exec .venv/bin/python3 pipeline/app.py
