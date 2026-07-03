# pipeline/setup.ps1
# One-command installer: checks each Brelly pipeline requirement and
# installs what's missing (no per-step prompts by default), then launches
# the app. Run from anywhere:
#   .\pipeline\setup.ps1
#   .\pipeline\setup.ps1 -Verbose        # stream full installer output
#   .\pipeline\setup.ps1 -Interactive    # confirm before each install
#
# Note: winget installs below pass --silent plus --accept-*-agreements to
# avoid GUI installer prompts and license confirmations. The one thing that
# can't be scripted away is a Windows UAC elevation prompt, if a package
# requires admin rights — that's the OS asking, not this script, and must
# stay live. Running this script from an already-elevated (Run as
# Administrator) terminal avoids per-package UAC prompts entirely.

param(
    [switch]$Verbose,
    [switch]$Interactive
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Confirm-Step {
    param([string]$Prompt)
    if (-not $Interactive) {
        return $true
    }
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

# Runs a non-interactive install command. In verbose mode, streams its
# output live. Otherwise shows a spinner with elapsed time and only prints
# the captured output if the command fails. Every winget call also passes
# --accept-*-agreements so a hidden license prompt can never make this look
# like it's hung.
function Run-Step {
    param(
        [string]$Description,
        [string]$FilePath,
        [string[]]$ArgumentList
    )
    if ($Verbose) {
        & $FilePath @ArgumentList
        return $LASTEXITCODE
    }

    $stdout = New-TemporaryFile
    $stderr = New-TemporaryFile
    $proc = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -NoNewWindow -PassThru `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $spin = '|', '/', '-', '\'
    $i = 0
    while (-not $proc.HasExited) {
        $elapsed = [int]((Get-Date) - $proc.StartTime).TotalSeconds
        Write-Host -NoNewline ("`r  {0}... {1} ({2}s)   " -f $Description, $spin[$i % 4], $elapsed)
        $i++
        Start-Sleep -Milliseconds 200
    }
    $proc.WaitForExit()
    $elapsed = [int]((Get-Date) - $proc.StartTime).TotalSeconds
    $exitCode = $proc.ExitCode
    if ($exitCode -eq 0) {
        Write-Host ("`r  {0}... done ({1}s)          " -f $Description, $elapsed)
    } else {
        Write-Host ("`r  {0}... failed ({1}s)          " -f $Description, $elapsed)
        Get-Content $stdout, $stderr -ErrorAction SilentlyContinue | Write-Host
    }
    Remove-Item $stdout, $stderr -ErrorAction SilentlyContinue
    return $exitCode
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
        $exit = Run-Step "Installing Python 3.12" "winget" @("install", "Python.Python.3.12", "--accept-package-agreements", "--accept-source-agreements", "--silent")
        if ($exit -ne 0) { Step-Failed "winget install Python.Python.3.12 failed." }
    } else {
        Step-Failed "Python 3.12 is required."
    }
}
try { py -3.12 --version | Out-Null } catch { Step-Failed "Python 3.12 still not found after install attempt." }
Write-Host "OK Python 3.12" -ForegroundColor Green

# 2. Blender
$blenderOk = [bool](Get-Command blender -ErrorAction SilentlyContinue)
if (-not $blenderOk) {
    Write-Host ""
    Write-Host "X Blender not found." -ForegroundColor Red
    Write-Host "  Will run: winget install BlenderFoundation.Blender"
    if (Confirm-Step "Proceed?") {
        $exit = Run-Step "Installing Blender" "winget" @("install", "BlenderFoundation.Blender", "--accept-package-agreements", "--accept-source-agreements", "--silent")
        if ($exit -ne 0) { Step-Failed "winget install BlenderFoundation.Blender failed." }
    } else {
        Step-Failed "Blender is required."
    }
}
if (-not (Get-Command blender -ErrorAction SilentlyContinue)) {
    Step-Failed "Blender still not found after install attempt."
}
Write-Host "OK Blender" -ForegroundColor Green

# 3. Node.js (needed to install gltfpack, which ships as an npm package)
$nodeOk = [bool](Get-Command npm -ErrorAction SilentlyContinue)
if (-not $nodeOk) {
    Write-Host ""
    Write-Host "X Node.js not found." -ForegroundColor Red
    Write-Host "  Will run: winget install OpenJS.NodeJS.LTS"
    if (Confirm-Step "Proceed?") {
        $exit = Run-Step "Installing Node.js" "winget" @("install", "OpenJS.NodeJS.LTS", "--accept-package-agreements", "--accept-source-agreements", "--silent")
        if ($exit -ne 0) { Step-Failed "winget install OpenJS.NodeJS.LTS failed." }
    } else {
        Step-Failed "Node.js is required to install gltfpack."
    }
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Step-Failed "Node.js still not found after install attempt."
}
Write-Host "OK Node.js" -ForegroundColor Green

# 4. gltfpack (published on npm with prebuilt binaries)
if (-not (Get-Command gltfpack -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "X gltfpack not found." -ForegroundColor Red
    Write-Host "  Will run: npm install -g gltfpack"
    if (Confirm-Step "Proceed?") {
        $exit = Run-Step "Installing gltfpack" "npm" @("install", "-g", "gltfpack")
        if ($exit -ne 0) { Step-Failed "npm install -g gltfpack failed. Download manually from https://github.com/zeux/meshoptimizer/releases" }
    } else {
        Step-Failed "gltfpack is required. Download manually from https://github.com/zeux/meshoptimizer/releases"
    }
}
if (-not (Get-Command gltfpack -ErrorAction SilentlyContinue)) {
    Step-Failed "gltfpack still not found after install attempt."
}
Write-Host "OK gltfpack" -ForegroundColor Green

# 5. Virtual environment
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host ""
    Write-Host "X Virtual environment not found." -ForegroundColor Red
    Write-Host "  Will run: py -3.12 -m venv .venv"
    if (Confirm-Step "Proceed?") {
        $exit = Run-Step "Creating virtual environment" "py" @("-3.12", "-m", "venv", ".venv")
        if ($exit -ne 0) { Step-Failed "py -3.12 -m venv .venv failed." }
    } else {
        Step-Failed "A virtual environment is required."
    }
}
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Step-Failed "Virtual environment still missing after creation attempt."
}
Write-Host "OK Virtual environment" -ForegroundColor Green

# 6. Python dependencies (also verifies GDAL — see note above)
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
        $exit = Run-Step "Installing Python dependencies" ".venv\Scripts\pip.exe" @("install", "-r", "pipeline\requirements.txt")
        if ($exit -ne 0) { Step-Failed ".venv\Scripts\pip.exe install -r pipeline\requirements.txt failed." }
    } else {
        Step-Failed "Python dependencies are required. See pipeline\SETUP_WINDOWS.md if GDAL install fails."
    }
}
& .venv\Scripts\python.exe -c "from osgeo import gdal; import pyproj, shapely, numpy" 2>$null
if ($LASTEXITCODE -ne 0) {
    Step-Failed "Dependencies still not importable after install attempt. See pipeline\SETUP_WINDOWS.md for GDAL/OSGeo4W troubleshooting."
}
Write-Host "OK Python dependencies" -ForegroundColor Green

# 7. Launch the app
Write-Host ""
Write-Host "All requirements satisfied. Launching Brelly Pipeline app..."
& .venv\Scripts\python.exe pipeline\app.py
