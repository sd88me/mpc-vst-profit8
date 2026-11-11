#!/usr/bin/env bash
# The catalog-shaped release zips, from the release build (build/"sd88me - VST - Profit-08", made by ./build.sh):
#   dist/Profit-08-<ver>-mpc-armv7.zip, dist/Profit-08-<ver>-mpc-aarch64.zip   one per CPU, made by mpc-vst-plugins' tools/release.py
# As 0.1.x, the .so is profit_08.so at the folder root, so the installer upgrades a 0.1.x install in place; Preset_Banks/ and
# profit08-favourites.dat are user data, kept on upgrade and uninstall. MPC_VST: an mpc-vst-plugins checkout with tools/release.py.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
MPC_VST="${MPC_VST:-$HOME/mpc-vst-plugins-postlaunch}"
[ -f "$MPC_VST/tools/release.py" ] || { echo "need mpc-vst-plugins with tools/release.py (MPC_VST)" >&2; exit 1; }
DIR="sd88me - VST - Profit-08"; SRC="$here/build/$DIR"
[ -f "$SRC/VST/profit08-arm32.so" ] || { echo "missing $SRC: run ./build.sh first" >&2; exit 1; }
VER=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$SRC/plugin.json")
python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); sys.exit(0 if m["uid"]=="Pft8" and "Beta" not in m["name"] else "not the release identity")' "$SRC/plugin.json"
out="$here/dist"; mkdir -p "$out"
for pair in armv7:arm32:file32 aarch64:arm64:file64; do
  IFS=: read -r cpu so key <<<"$pair"
  st="$here/build/catalog/$cpu"; rm -rf "$st"; mkdir -p "$st/$DIR"
  cp -r "$SRC/Plugin Skins" "$SRC/version.xml" "$st/$DIR/"
  python3 - "$SRC/plugin.json" "$st/$DIR/plugin.json" "$key" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
m.pop("file32", None); m.pop("file64", None)
m[sys.argv[3]] = "profit_08.so"
json.dump(m, open(sys.argv[2], "w"), indent=2)
PY
  cp "$SRC/VST/profit08-$so.so" "$st/profit_08.so"
  printf '<PLUGIN name="Profit-08" descriptiveName="Profit-08" format="VST" category="Synth" manufacturer="sd88me" version="%s" file="profit_08.so" uid="50667438" isInstrument="1" fileTime="0" infoUpdateTime="0" numInputs="0" numOutputs="2" isShell="0"/>\n' "$VER" > "$st/entry.xml"
  python3 "$MPC_VST/tools/release.py" --so "$st/profit_08.so" --skin "$st/$DIR" --entry "$st/entry.xml" --version "$VER" \
    --user-data Preset_Banks --user-data profit08-favourites.dat \
    --repo sd88me/mpc-vst-profit8 --license MIT --id profit-08 \
    --about "Eight-voice, two-layer analog-style synthesizer with sequencer, arpeggiator and modulation matrix; native MPC skin with favourites." \
    -o "$st/dist"
  z=$(ls "$st/dist"/*.zip); cp "$z" "$out/Profit-08-$VER-mpc-$cpu.zip"
done
ls -la "$out"/Profit-08-"$VER"-mpc-*.zip
