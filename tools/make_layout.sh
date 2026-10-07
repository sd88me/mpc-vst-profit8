#!/usr/bin/env bash
# Regenerate vst/params.json, src/patch_tab.h and (when present) vst/layout.conf.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$HERE/tools/gen_patch.py" --params > "$HERE/vst/params.json"
python3 "$HERE/tools/gen_patch.py" --header > "$HERE/src/patch_tab.h"
[ -f "$HERE/tools/gen_layout.py" ] && python3 "$HERE/tools/gen_layout.py"
echo "wrote vst/params.json, src/patch_tab.h"
