#!/usr/bin/env bash
# Run from the Brelly project root: bash pipeline/check_system.sh
_chk() { "$@" &>/dev/null && echo ok || echo missing; }
echo "HOMEBREW=$(_chk brew --version)"
echo "PYTHON312=$(_chk python3.12 --version)"
echo "GDAL_SYS=$(_chk gdal-config --version)"
echo "VENV=$([ -f .venv/bin/python3 ] && echo ok || echo missing)"
echo "DEPS=$(_chk .venv/bin/python3 -c 'from osgeo import gdal; import pyproj, shapely, numpy')"
echo "BLENDER=$(_chk blender --version)"
echo "GLTFPACK=$(_chk gltfpack --version)"
echo "DATA_DEM=$([ -f data/alti3d.tif ] && echo ok || echo missing)"
echo "DATA_TLM=$([ -f data/swissTLM3D.gpkg ] && echo ok || echo missing)"
echo "CONFIG=$(ls pipeline/config/*.json 2>/dev/null | grep -v example.json | head -1 | grep -q . && echo ok || echo missing)"
