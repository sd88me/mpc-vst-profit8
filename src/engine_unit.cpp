// The C engine (src/engine.c, curves.c, syx.c) compiled as C++ for the native build, which builds only top-level .cpp files
// in src/. The same sources still build as C for the 1.x wrapper build (vst/build.sh). mpc_engine() keeps C linkage (engine.h).
#include "engine.c"
#include "curves.c"
#include "syx.c"
