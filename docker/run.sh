#!/usr/bin/env bash
# docker/run.sh
# Build (if needed) and run the Brelly pipeline "clean machine" container,
# forwarding X11 to the host so pipeline/app.py's Tkinter GUI can display.
#
# macOS prerequisite: XQuartz (https://www.xquartz.org/), with
# "Allow connections from network clients" enabled in
# XQuartz > Settings > Security, then log out/in once after installing.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

IMAGE="brelly-pipeline-clean"

echo "==> Building image (only re-runs steps whose inputs changed)"
docker build -f docker/Dockerfile -t "$IMAGE" .

if [[ "$(uname)" == "Darwin" ]]; then
  echo "==> Allowing X11 connections from Docker via XQuartz"
  xhost + 127.0.0.1 >/dev/null 2>&1 || {
    echo "xhost not found or XQuartz not running — start XQuartz first: open -a XQuartz"
    exit 1
  }
fi

echo "==> Running container (data/ and maps/ mounted so output persists on host)"
docker run --rm -it \
  -e DISPLAY=host.docker.internal:0 \
  -v "$PROJECT_ROOT/data:/brelly/data" \
  -v "$PROJECT_ROOT/maps:/brelly/maps" \
  -v "$PROJECT_ROOT/pipeline/config:/brelly/pipeline/config" \
  "$IMAGE"
