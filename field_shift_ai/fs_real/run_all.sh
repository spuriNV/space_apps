#!/usr/bin/env bash
# Rebuild inputs, train/test/validate both models, and draw the charts (California preset).
set -euo pipefail
cd "$(dirname "$0")"
python3 merge_s2.py
python3 build_ca_obs.py
python3 build_ca_weekly.py
python3 run_b61.py
python3 run_b62.py
python3 plot_b61.py
python3 plot_b62.py "MODIS NDVI + LST, SERVIR ESI 4-wk, NASA-USDA SMAP / POWER soil wetness, GPM IMERG / POWER rain, POWER ETo"
