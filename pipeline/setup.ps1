# pipeline/setup.ps1
# One-command installer: checks each Brelly pipeline requirement, asks to
# install what's missing, then launches the app. Run from anywhere:
#   .\pipeline\setup.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Confirm-Step {
    param([string]$Prompt)
    $reply = Read-Host "$Prompt [y/N]"
    return $reply -match '^[Yy]'
}

function Step-Failed {
    param([string]$Message)
    Write-Host ""
    Write-Host "X $Message" -ForegroundColor Red
    Write-Host "  Run this manually, then re-run: .\pipeline\setup.ps1"
    exit 1
}

Write-Host "Brelly pipeline setup"
Write-Host "======================"

# 1. Python 3.12
$pythonOk = $false
try { py -3.12 --version | Out-Null; $pythonOk = $true } catch { $pythonOk = $false }
if (-not $pythonOk) {
    Write-Host ""
    Write-Host "X Python 3.12 not found." -ForegroundColor Red
    Write-Host "  Will run: winget install Python.Python.3.12"
    if (Confirm-Step "Proceed?") {
        winget install Python.Python.3.12
    } else {
        Step-Failed "Python 3.12 is required."
    }
}
try { py -3.12 --version | Out-Null } catch { Step-Failed "Python 3.12 still not found after install attempt." }
Write-Host "OK Python 3.12"

# 2. Blender
$blenderOk = [bool](Get-Command blender -ErrorAction SilentlyContinue)
if (-not $blenderOk) {
    Write-Host ""
    Write-Host "X Blender not found." -ForegroundColor Red
    Write-Host "  Will run: winget install BlenderFoundation.Blender"
    if (Confirm-Step "Proceed?") {
        winget install BlenderFoundation.Blender
    } else {
        Step-Failed "Blender is required."
    }
}
if (-not (Get-Command blender -ErrorAction SilentlyContinue)) {
    Step-Failed "Blender still not found after install attempt."
}
Write-Host "OK Blender"

# 3. gltfpack (no package-manager formula on Windows — manual only)
if (-not (Get-Command gltfpack -ErrorAction SilentlyContinue)) {
    Step-Failed "gltfpack not found. Download manually from https://github.com/zeux/meshoptimizer/releases, add it to PATH, then re-run this script."
}
Write-Host "OK gltfpack"

# 4. Virtual environment
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host ""
    Write-Host "X Virtual environment not found." -ForegroundColor Red
    Write-Host "  Will run: py -3.12 -m venv .venv"
    if (Confirm-Step "Proceed?") {
        py -3.12 -m venv .venv
    } else {
        Step-Failed "A virtual environment is required."
    }
}
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Step-Failed "Virtual environment still missing after creation attempt."
}
Write-Host "OK Virtual environment"

# 5. Python dependencies (also verifies GDAL — see note above)
$depsOk = $false
try {
    & .venv\Scripts\python.exe -c "from osgeo import gdal; import pyproj, shapely, numpy" 2>$null
    if ($LASTEXITCODE -eq 0) { $depsOk = $true }
} catch { $depsOk = $false }
if (-not $depsOk) {
    Write-Host ""
    Write-Host "X Python dependencies not installed (this also covers GDAL bindings)." -ForegroundColor Red
    Write-Host "  Will run: .venv\Scripts\pip.exe install -r pipeline\requirements.txt"
    if (Confirm-Step "Proceed?") {
        & .venv\Scripts\pip.exe install -r pipeline\requirements.txt
    } else {
        Step-Failed "Python dependencies are required. See pipeline\SETUP_WINDOWS.md if GDAL install fails."
    }
}
& .venv\Scripts\python.exe -c "from osgeo import gdal; import pyproj, shapely, numpy" 2>$null
if ($LASTEXITCODE -ne 0) {
    Step-Failed "Dependencies still not importable after install attempt. See pipeline\SETUP_WINDOWS.md for GDAL/OSGeo4W troubleshooting."
}
Write-Host "OK Python dependencies"

# 6. Launch the app
Write-Host ""
Write-Host "All requirements satisfied. Launching Brelly Pipeline app..."
& .venv\Scripts\python.exe pipeline\app.py
