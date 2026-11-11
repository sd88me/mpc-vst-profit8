#!/usr/bin/env bash
# tests/data/legacy-0.1.3.chunk: the chunk a project saved with the released 0.1.3 build holds, made by that build's own engine code
# (git tag profit-08-v0.1.3) driven by tests/legacy_dump.c. Holds only the engine's init program with a few edits.
set -euo pipefail
cd "$(dirname "$0")/.."
MV="${MPC_VST:-$PWD/../mpc-vst-plugins}"
w="$(mktemp -d)"; trap 'rm -rf "$w"' EXIT
git archive profit-08-v0.1.3 src analog | tar -x -C "$w"
gcc -std=gnu11 -O1 -w -I"$w/src" -I"$w/analog" -I"$MV/wrapper" -o "$w/dump" tests/legacy_dump.c "$w/src/engine.c" "$w/src/curves.c" "$w/src/syx.c" -lm
mkdir -p "$w/data" tests/data
"$w/dump" "$w/data" > tests/data/legacy-0.1.3.chunk
printf '\0' >> tests/data/legacy-0.1.3.chunk   # the wrapper saved the string with its NUL
echo "tests/data/legacy-0.1.3.chunk: $(wc -c < tests/data/legacy-0.1.3.chunk) bytes"
