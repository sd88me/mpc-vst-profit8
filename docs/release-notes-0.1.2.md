Profit-08 0.1.2: first release with a Gen2 (aarch64) build alongside the Gen1/Force armv7 build. The plugin itself is unchanged from 0.1.1.

**New: Gen2 build.** `Profit-08-0.1.2-mpc-aarch64.zip` is for Gen2 devices (MPC Live III and kin, MPC OS 3.x); `Profit-08-0.1.2-mpc-armv7.zip` is for the Force and the other first-generation devices. Same source as 0.1.1 in both.

**Status:** the Gen2 build was tested on an MPC Live III (MPC OS 3.9.1) by a Gen2 tester, as the 0.1.1 Gen2 test build, and the armv7 build on a Force (MPC OS 3.9.1). MPC OS 3.x only (the screen skin format).

Eight-voice, two-layer analog-style synthesizer: layers A and B as normal, stack and split, unison, a gated sequencer and an arpeggiator per layer, two oscillators and a resonant 2/4-pole lowpass per voice, three envelopes, four LFOs and the modulation matrix. Its program is the instrument's own 384 bytes, so its program and bank SysEx dumps load unchanged. Native MPC screen skin with Q-Link pages; banks and programs browser.

**No factory sounds are included.** Put your own `.syx` program or bank dumps in `Preset_Banks/` inside the plugin folder (`/sdcard/Synths/sd88me - VST - Profit-08/`); the installer keeps them across upgrades.

## Requirements
- A Gen1 (32-bit ARM: Force, MPC Live / Live II, One, X, Key 61) or Gen2 (64-bit, MPC Live III and kin) MPC OS standalone device. The installer picks the right build by the zip; it refuses the wrong architecture.
- **Root shell access** (SSH) to the device. Stock MPC OS doesn't offer this; you need a modded unit.
- Installing plugins this way is unofficial: back up first, use at your own risk.

## Install
1. Unzip the one for your device, then copy the folder to the device, e.g. `scp -r Profit-08-0.1.2 root@<device-ip>:/tmp/`
2. Run it: `ssh root@<device-ip> sh /tmp/Profit-08-0.1.2/install.sh`

*Profit-08 is an independent project, not affiliated with or endorsed by Dave Smith Instruments or Sequential.*
