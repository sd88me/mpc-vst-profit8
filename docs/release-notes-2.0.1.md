# Profit-08 2.0.1

A fix release. The sound engine and the screen are unchanged.

## Fixed
- A knob or Q-Link move could be put back to its previous value when it came just as the plugin was refreshing the screen (for example right after a
  program change). The new value now always stays.

## Compatibility
- Same parameters and project format as 2.0.0 and 0.1.x; programs, favourites and projects load unchanged.

## Tested
Offline: the host test and the host simulator's parameter sweep, which caught the problem.
