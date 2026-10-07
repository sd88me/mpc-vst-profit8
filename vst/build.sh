#!/usr/bin/env bash
# Builds the armhf plugin and the skin into vst/build/ (needs Docker; ../mpc-vst-plugins checked out next to this repo, or MPC_VST set).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MV="${MPC_VST:-$HERE/../../mpc-vst-plugins}"
"$HERE/../tools/make_layout.sh"
exec "$MV/tools/build_port.sh" "$HERE/vst.json"
