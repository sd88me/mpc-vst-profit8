# Profit-08 2.0.0

Profit-08 2.0.0 adds a native MPC screen and Q-Link mapping. The sound engine is unchanged.

## What's new
- Native MPC screen: six tabs (PROGRAM, BANKS, OSC/FILTER, AMP/LFO, MODS, SEQ) with the Profit-08 knobs, and Q-Links mapped to every page.
- Bigger knobs, labels and values.
- BANKS page: tile lists of banks and programs, page buttons, and favourites (+ FAV / - FAV, saved in `profit08-favourites.dat`).
- The data wheel steps one program at a time on the BANKS readouts.
- Quality defaults to High 2x on 64-bit MPCs (Live, One, X, Key) and Eco 1x on the Force; you can still change it.
- One zip holds the 32-bit (Force) and 64-bit builds.

## Compatibility
- Parameter order and the project chunk format of 0.1.x are kept, so projects saved with 0.1.3 should load.
- Put `.syx` program/bank dumps in `Preset_Banks/` as before; none are shipped.

## Tested
Live III (all pages, banks, favourites, Q-Links) and the Force (loads, PROGRAM/BANKS/AMP pages, CPU about 12% of one core with 8 voices at Eco).
Not yet tested: every Force page, a real project saved with 0.1.3, save and reload of a 2.0 project, sound compared by ear.
