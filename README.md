# Profit-08

An eight-voice, two-layer analog-style synthesizer for Akai MPC OS standalone devices (Force, MPC Live / One / X / Key), built as a native VST2
instrument with its own MPC screen. It plays the way the Prophet '08 does: two analog-style oscillators per voice with hard sync, a 2/4-pole resonant lowpass, three envelopes, four
LFOs, four mod slots and controller routes, a 4 x 16 gated sequencer and an arpeggiator, layers A and B combined as stacks and splits. Its program is the
instrument's own 384 bytes, so its program and bank SysEx dumps (including the factory banks) load unchanged.

*Profit-08 is an independent project, not affiliated with or endorsed by Dave Smith Instruments or Sequential. The name is a pun on the instrument it is modelled on.*

![Profit-08 on an MPC: the Program page](docs/img/screenshot-program.png)

| | |
|---|---|
| ![Banks and favourites](docs/img/screenshot-banks.png) | ![Oscillators and filter](docs/img/screenshot-osc.png) |
| ![Amp, envelopes and LFOs](docs/img/screenshot-amp.png) | ![Modulators and controllers](docs/img/screenshot-mods.png) |
| ![Sequencer](docs/img/screenshot-seq1.png) | ![Filter sub-tab](docs/img/screenshot-filter.png) |

## New in 2.0
- **Native MPC screen**: six tabs (PROGRAM, BANKS, OSC/FILTER, AMP/LFO, MODS, SEQ) drawn in the Profit-08 look, with large knobs and readable labels and values.
- **Q-Links** control every page: four groups of four per tab, matching the panels on screen.
- **BANKS page**: tile lists for banks and programs, page buttons in the Programs header, a **RANDOM** button (a random bank and program), and **favourites**: `+ FAV` opens a keyboard to name the sound (up to 20 characters; SHIFT for a capital, DEL, SPACE, CANCEL, SAVE), `- FAV` deletes the picked one. They are kept in `profit08-favourites.dat`.
- **Data wheel** steps one program at a time on the BANKS readouts.
- **Quality** defaults to High 2x on 64-bit MPCs (Live, One, X, Key) and Eco 1x on the Force.
- One zip carries the 32-bit (Force) and 64-bit builds; programs and projects from 0.1.x load unchanged.

**Status: 2.0.1 released** (docs/release-notes-2.0.1.md, docs/STATUS.md). Tested on a Live III; the Force has had a shorter check (loads, PROGRAM, BANKS and AMP pages).

## Preset banks
The plugin makes a folder called `Preset_Banks` inside its own folder on first load. Put `.syx` files there (a folder named `Preset Banks` is read too) (program dumps or bank dumps from the instrument,
including the factory banks `Prophet_08_Programs_v1.0.syx`, which DSI publishes). Each bank in a file becomes a bank on the program page, named after the file.
No factory programs are shipped.

## Backing up your favourites and sounds

Your favourites and your own files are kept in the plugin folder on the MPC, not in your projects (a project keeps only the sound its
track uses). Back them up before you update the plugin or MPC OS, reset the device, or move to another MPC. These are the files to keep,
inside the plugin folder `sd88me - VST - Profit-08`:

| File or folder | What it holds |
|---|---|
| `profit08-favourites.dat` | your favourites (+FAV) |
| `Preset_Banks/` | your `.syx` banks (an install from 1.x may keep them in `Content/Preset_Banks/` instead) |

### Where the plugin folder is
It is in `VST2 Plugins` on one of the MPC's drives, or in a Synths folder (`/sdcard/Synths`, or `/nvme/Synths` on a Live III),
depending on how Profit-08 was installed. Over SSH (root access), this prints its path:

```bash
ssh root@<device-ip> 'find /sdcard /nvme /media -maxdepth 3 -type d -name "sd88me - VST - Profit-08" 2>/dev/null'
```

### Backing up
- **The plugin folder is on an SD card or USB drive:** plug the drive into a computer and copy the files above to it.
- **Over SSH**, from a computer: this copies the whole plugin folder into one file, `profit8-backup.tar`. Put the folder that holds the
  plugin folder (the path above without its last part) in place of `<parent folder>`:

  ```bash
  ssh root@<device-ip> 'cd "<parent folder>" && tar cf - "sd88me - VST - Profit-08"' > profit8-backup.tar
  ```

### Restoring
Install Profit-08 first (on the new device, or after the reset or update), then put back only the files above. Don't copy the whole
old folder over the new one: that would put the old version of the plugin back too.

- **From a drive:** copy the files back to the same places in the new plugin folder.
- **Over SSH:** unpack the backup on your computer and send the files back. List only the ones your backup has, and put the new
  plugin folder's path (found as above) in place of `<plugin folder>`:

  ```bash
  mkdir profit8-backup && tar xf profit8-backup.tar -C profit8-backup
  tar cf - -C "profit8-backup/sd88me - VST - Profit-08" "profit08-favourites.dat" "Preset_Banks" | ssh root@<device-ip> 'cd "<plugin folder>" && tar xf -'
  ```

Then remove Profit-08 from its tracks and add it again (or reopen the project), so it reads the restored files.

## How it was derived
The instrument's two OS updates (main, voice) were decoded offline with `tools/fw/`; they hold the unison detune table and a time table, not the factory
sounds or waves, and the analog sound is a model (`analog/`, shared with Morpho-PE and Sturm). See docs/FIRMWARE.md for what is exact, fitted and assumed.

## Building and testing
`./build.sh` builds the 2.0 plugin (set `MPC_BUILDER` to the MPC plugin builder checkout) and `./build.sh test` also runs the offline host test (`tests/run.sh`); `tools/make_layout.sh` regenerates the 1.x parameter tables;
`gcc -O2 -Isrc -Ianalog -I../mpc-vst-plugins/wrapper test/test_engine.c src/engine.c src/curves.c src/syx.c -lm && ./a.out DIR` runs the engine test
(DIR holds a `Preset_Banks` folder with your own `.syx` files).

## Credits
The wordmark's letter outlines come from the font Almendra (SIL Open Font License 1.1, Ana Sanfelippo, via Google Fonts), converted to paths by `tools/make_wordmark.py`.
