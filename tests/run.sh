#!/usr/bin/env bash
# Offline x86 test under ASan/UBSan (no device): the native front end + the real engine, driven by tests/host_test.cpp. Must print OK.
# P8_NAME: the build's name (beta tests). No banks are needed: the engine's init bank is used.
set -euo pipefail
cd "$(dirname "$0")/.."
BUILDER="${MPC_BUILDER:-$HOME/mpc-plugin-builder}"
python3 tools/gen_params.py >/dev/null
[ -f tests/data/legacy-0.1.3.chunk ] || tests/make_legacy_chunk.sh >/dev/null
T=build/test; mkdir -p "$T"
S="-fsanitize=address,undefined -fno-sanitize-recover=undefined -O1 -g -std=c++17 -pthread"
g++ $S -Wall -DP8_TEST -DP8_EXPECT_NAME="\"${P8_NAME:-Profit-08}\"" ${P8_NAME:+-DP8_NAME="\"$P8_NAME\""} -I"$BUILDER/framework" -Isrc \
  -o "$T/p8test" src/Profit08Plugin.cpp src/engine_unit.cpp tests/host_test.cpp -lm
pf="$(mktemp -d)"; trap 'rm -rf "$pf"' EXIT
cp plugin.json "$pf/" 2>/dev/null || true
MPC_PLUGIN_FOLDER="$pf" ASAN_OPTIONS=detect_leaks=1 "$T/p8test" tests/data/legacy-0.1.3.chunk
