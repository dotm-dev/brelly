# docker/Dockerfile
#
# Simulates a "clean machine" for the Brelly pipeline setup process:
# system deps -> venv -> pip install -> launch pipeline/app.py.
#
# Ubuntu 24.04 ships Python 3.12 by default, matching the pipeline's
# required version. Blender and gltfpack are intentionally skipped —
# this image only needs to get you to the app launching (System Check /
# New Map / Run tabs); it doesn't bake meshes.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Mirrors pipeline/setup.sh steps 2-3 (Python 3.12 + GDAL), plus tkinter
# (app.py's GUI toolkit) and git/curl for cloning + convenience.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-tk \
    gdal-bin \
    libgdal-dev \
    build-essential \
    git \
    curl \
    ca-certificates \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /brelly

# Copy just the pipeline first so the venv/pip-install layer caches
# independently of the rest of the repo (src/, maps/, etc.).
COPY pipeline/ pipeline/

# Step 6-7 of setup.sh: create venv, install Python dependencies.
# GDAL's Python bindings must match the system libgdal version exactly
# (Ubuntu 24.04 ships 3.8.4), so it's pinned separately before the rest
# of requirements.txt, which has it as an open-ended >= constraint.
RUN python3.12 -m venv .venv && \
    .venv/bin/pip install --no-cache-dir "gdal==$(gdal-config --version)" && \
    .venv/bin/pip install --no-cache-dir -r pipeline/requirements.txt

# Sanity check, same import test setup.sh uses.
RUN .venv/bin/python3 -c "from osgeo import gdal; import pyproj, shapely, numpy"

ENV DISPLAY=host.docker.internal:0

CMD [".venv/bin/python3", "pipeline/app.py"]
