#!/usr/bin/env bash
# pipeline/setup.sh
# One-command installer: checks each Brelly pipeline requirement, asks to
# install what's missing, then launches the app. Run from anywhere:
#   bash pipeline/setup.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

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
  read -r -p "$prompt [y/N] " reply
  case "$reply" in
    [yY][eE][sS]|[yY]) return 0 ;;
    *) return 1 ;;
  esac
}

step_failed() {
  echo ""
  echo "✗ $1"
  echo "  Run this manually, then re-run: bash pipeline/setup.sh"
  exit 1
}

echo "Brelly pipeline setup"
echo "======================"

# 1. Homebrew
if ! command -v brew >/dev/null 2>&1; then
  echo ""
  echo "✗ Homebrew not found."
  echo "  Will run: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
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
echo "✓ Homebrew"

# 2. Python 3.12
if ! command -v python3.12 >/dev/null 2>&1; then
  echo ""
  echo "✗ Python 3.12 not found."
  echo "  Will run: brew install python@3.12"
  if confirm "Proceed?"; then
    brew install python@3.12
  else
    step_failed "Python 3.12 is required."
  fi
fi
command -v python3.12 >/dev/null 2>&1 || step_failed "Python 3.12 still not found after install attempt."
echo "✓ Python 3.12"

# 2b. tkinter (app.py's GUI toolkit; Homebrew's python@3.12 doesn't bundle Tk)
if ! python3.12 -c "import tkinter" >/dev/null 2>&1; then
  echo ""
  echo "✗ tkinter not found."
  echo "  Will run: brew install python-tk@3.12"
  if confirm "Proceed?"; then
    brew install python-tk@3.12
  else
    step_failed "tkinter is required to launch the pipeline app."
  fi
fi
python3.12 -c "import tkinter" >/dev/null 2>&1 || step_failed "tkinter still not importable after install attempt."
echo "✓ tkinter"

# 3. GDAL system library
if ! command -v gdal-config >/dev/null 2>&1; then
  echo ""
  echo "✗ GDAL system library not found."
  echo "  Will run: brew install gdal"
  if confirm "Proceed?"; then
    brew install gdal
  else
    step_failed "GDAL is required."
  fi
fi
command -v gdal-config >/dev/null 2>&1 || step_failed "GDAL still not found after install attempt."
echo "✓ GDAL system library"

# 4. Blender
if ! command -v blender >/dev/null 2>&1; then
  echo ""
  echo "✗ Blender not found."
  echo "  Will run: brew install --cask blender"
  if confirm "Proceed?"; then
    brew install --cask blender
  else
    step_failed "Blender is required."
  fi
fi
command -v blender >/dev/null 2>&1 || step_failed "Blender still not found after install attempt."
echo "✓ Blender"

# 5. Node.js (needed to install gltfpack, which ships as an npm package —
# there's no Homebrew formula for it)
if ! command -v npm >/dev/null 2>&1; then
  echo ""
  echo "✗ Node.js not found."
  echo "  Will run: brew install node"
  if confirm "Proceed?"; then
    brew install node
  else
    step_failed "Node.js is required to install gltfpack."
  fi
fi
command -v npm >/dev/null 2>&1 || step_failed "Node.js still not found after install attempt."
echo "✓ Node.js"

# 6. gltfpack (published on npm with prebuilt binaries; no Homebrew formula)
if ! command -v gltfpack >/dev/null 2>&1; then
  echo ""
  echo "✗ gltfpack not found."
  echo "  Will run: npm install -g gltfpack"
  if confirm "Proceed?"; then
    if ! npm install -g gltfpack; then
      step_failed "npm install -g gltfpack failed. Download manually from https://github.com/zeux/meshoptimizer/releases"
    fi
  else
    step_failed "gltfpack is required. Download manually from https://github.com/zeux/meshoptimizer/releases"
  fi
fi
command -v gltfpack >/dev/null 2>&1 || step_failed "gltfpack still not found after install attempt."
echo "✓ gltfpack"

# 7. Virtual environment
if [ ! -f ".venv/bin/python3" ]; then
  echo ""
  echo "✗ Virtual environment not found."
  echo "  Will run: python3.12 -m venv .venv"
  if confirm "Proceed?"; then
    python3.12 -m venv .venv
  else
    step_failed "A virtual environment is required."
  fi
fi
[ -f ".venv/bin/python3" ] || step_failed "Virtual environment still missing after creation attempt."
echo "✓ Virtual environment"

# 8. Python dependencies
if ! .venv/bin/python3 -c "from osgeo import gdal; import pyproj, shapely, numpy" >/dev/null 2>&1; then
  echo ""
  echo "✗ Python dependencies not installed."
  echo "  Will run: .venv/bin/pip install -r pipeline/requirements.txt"
  if confirm "Proceed?"; then
    .venv/bin/pip install -r pipeline/requirements.txt
  else
    step_failed "Python dependencies are required."
  fi
fi
.venv/bin/python3 -c "from osgeo import gdal; import pyproj, shapely, numpy" >/dev/null 2>&1 || step_failed "Dependencies still not importable after install attempt."
echo "✓ Python dependencies"

# 9. Launch the app
echo ""
echo "All requirements satisfied. Launching Brelly Pipeline app..."
exec .venv/bin/python3 pipeline/app.py
