# Profit-8: agent guide

MPC OS VST2 instrument modelled on the Prophet '08 (eight voices, two layers). Start with `README.md`, `docs/STATUS.md` and
`docs/FIRMWARE.md`, then mpc-vst-plugins' (checked out next to this repo as `../mpc-vst-plugins`) `CLAUDE.md`, `docs/NOTES.md`
and `docs/PORTING.md`. Sibling ports to copy from: `../mpc-vst-morpho-PE` (source of `analog/mpc_analog.h`) and `../mpc-vst-sturm`.

Ground rules:
- Never commit the instrument's OS files, decoded images (`p8_fw.py unpack` output), extracted tables, factory or third-party banks
  (`.syx`), or recordings. The engine's curves are formulas and short breakpoint lists fitted to the firmware (document each fit in
  docs/FIRMWARE.md); `tools/fw/p8_fw.py` re-derives them from the user's own files. Banks go in the plugin's `Preset_Banks` folder at run time.
- No "Prophet", "DSI", "Dave Smith" or "Sequential" in the product name, plugin id or skin art; the README may say what it is modelled
  on, with the disclaimer.
- `vst/params.json` and `src/patch_tab.h` are generated: edit `tools/gen_patch.py` and run `tools/make_layout.sh`. Parameter order is
  the instrument's own program byte order and append-only once released.
- `analog/mpc_analog.h` is a synced copy of mpc-vst-morpho-PE's (`../mpc-vst-morpho-PE/analog/sync.sh --check analog`).
- Every release must be catalog-conformant (`release.py --repo sd88me/mpc-vst-profit8 --license MIT --id profit-8`, `catalog_check.py --catalog` OK).
