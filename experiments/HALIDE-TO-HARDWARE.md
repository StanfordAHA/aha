# Halide-to-Hardware changes — conv_3_3 Path B / split-mem schedules

Documentation of the modifications made to the `Halide-to-Hardware` subrepo
(`/aha/Halide-to-Hardware`) to enable multi-level (split-mem / Path B / 2-level)
Halide schedules for the `conv_3_3` hardware benchmark, plus the parameterized
`conv_3_3` generator used to drive the experiments.

Companion docs: [CLOCKWORK.md](CLOCKWORK.md) (the clockwork-side codegen fixes and
the full latency investigation), [LAKE.md](LAKE.md), [GARNET.md](GARNET.md).

## Branch & provenance

| | |
|---|---|
| Repo | `/aha/Halide-to-Hardware` (submodule of `/aha`, url `stanfordaha/Halide-to-Hardware`) |
| Branch | `max` (new branch created for this work) |
| Base | `272c652c2` (`Merge pull request #42 … zircon_ml_mapping`) — a shared ancestor on the `master` line |
| Our commit | `7d6dc01a8` — "conv_3_3 Path B / split-mem schedules: HW-xcel dedup + wrapper schedule inheritance" |
| Files | `src/ExtractHWAccelerators.cpp`, `src/CodeGen_Clockwork_Target.cpp`, `src/ScheduleFunctions.cpp`, `apps/hardware_benchmarks/tests/conv_3_3/{conv_3_3_generator.cpp, process.cpp, Makefile}` |

The base commit is not a branch tip — it is a merge commit that is an ancestor of
`master` and several `zircon_*` feature branches. `max` was created deliberately to
carry this work off that point.

## Overview

H2H lowers a Halide schedule into a clockwork `prog` via `emit_hardware_target()`. The
accelerator boundary is expressed with the `hw_output.in()` wrapper-Func idiom.
Multi-level schedules (tiling the wrapper and/or the source at MEM sub-tile grain) hit
three latent assumptions in H2H's lowering, each fixed below and each guarded so the
existing benchmark suite is unaffected. Regression-checked on branch `max`:
`conv_3_3` Path B = 2111 cyc gold=1; `gaussian` "Images are equivalent!" with no
vectorize error.

## Fix 1 — `InsertHWXcel` duplicate-wrap guard (`ExtractHWAccelerators.cpp`)

`InsertHWXcel` walks the IR and wraps the loop/producer matching `xcel.store_level`
in an `_hls_target.<xcel>` node. Some upstream passes (sliding-window prologue +
steady-state, or split-loop duplication) can leave **two sibling nodes** whose name
matches the store level. Both got wrapped, and downstream `CodeGen_RDAI` pushed the
same xcel name into `xcel_names` twice, tripping the `xcels.size() == 1` assertion.

**Fix.** A `bool matched` member; the first `visit(For*)` / `visit(ProducerConsumer*)`
match wraps and sets `matched = true`; any later match for the same xcel logs
`SKIPPING duplicate … match` and recurses via `IRMutator::visit(op)` (so nested passes
still see the loop) instead of wrapping again.

## Fix 2 — `add_kernel` dedup + Realize re-shift guard (`CodeGen_Clockwork_Target.cpp`)

Two independent guards:

- **`add_kernel` dedup.** When Halide's `TailStrategy` specializes a non-divisor tile
  into prologue/steady/epilogue code paths (e.g. Path B `schedule=3` with `mem_x=20`
  on a tilesize-62 axis), the single `_hls_target` PC node is textually duplicated
  into each specialization, so `CodeGen_RDAI` calls `add_kernel` repeatedly for the
  same xcel. Now the first call emits the prog and records the name; later calls with
  the same `printname(xcel_name)` log `SKIPPING duplicate xcel` and return early.

- **Realize re-shift guard** (`visit(const Realize*)`). If an op's realize bounds were
  already shifted by an outer variable-min `Realize`, shifting again would
  double-subtract the mins from the body's Provide/Call args and produce wrong output.
  The `realize_glb_indices` consumers are commented out, so skipping the re-shift is
  correct. This lets output-side sliding-window schedules
  (`hw_output.store_at(x,outer).compute_at(x,inner)`) pass the pass.

## Fix 3 — wrapper schedule inheritance, inlined-guarded (`ScheduleFunctions.cpp`)

When a materialized (non-inlined) accelerator-input wrapper has a *default flat* stage
schedule but its source Func has been `tile()`/`split()`, the wrapper is made to
inherit the source's splits + dims, so downstream lowering (H2H's
`CodeGen_Clockwork_Target`, then clockwork's delay-adjustment/banking) sees a
sub-tile-aware wrapper op instead of a flat one. It fires only when the wrapper's
schedule is untouched (`splits().empty()` and `dims().size() == n_args + 1`), so
user-applied tiling on the wrapper takes precedence.

**Guard (important).** The inheritance is skipped when the wrapper is inlined
(`f.schedule().store_level().is_inlined()`). Halide rejects vectorize/unroll/split on
inlined funcs; inheriting a source's vectorize (as in `gaussian`'s blur→hw_output
wrapper) tripped *"Cannot vectorize dimension x.v32 because the function is scheduled
inline"* at generator time. Only materialized wrappers benefit from the inherited
schedule anyway. This guard is what keeps `gaussian` (and the other benchmark apps)
unregressed.

## The parameterized conv_3_3 generator

`apps/hardware_benchmarks/tests/conv_3_3/conv_3_3_generator.cpp` is extended with
`GeneratorParam`s and a multi-branch schedule (all guarded under
`Target::Clockwork`; the `CoreIR`/`HLS` and CPU paths are unchanged):

| param | meaning |
|---|---|
| `in_img` | image side; `tilesize = in_img - ksize + 1` |
| `schedule` | 0/1/2/3/4 (see below) |
| `glb_x/y` | GLB tile size (0 = auto = tilesize) |
| `mem_x/y` | MEM/CGRA tile size (0 = auto = glb) |
| `sub_mem_x/y` | schedule=4 inner sub-tile (0 = auto = mem/2) |
| `unroll` | RDom unroll factor (default ksize=3) |

| schedule | shape |
|---|---|
| 0 | single-level: whole image is one hw tile (original default) |
| 1 | GLB outer + MEM/CGRA inner (naive split-mem — the 3.55× penalty case) |
| 2 | 3-level: host → GLB → MEM/CGRA |
| **3** | **Path B**: wrapper tiled at MEM grain so each MEM sub-tile is its own accelerator invocation (uses distinct wrapper Vars `wxi/wyi/wxo/wyo` to sidestep `.in()`-vs-source Var aliasing). This is the winner. |
| 4 | 2-level nested Path B: wrapper at MEM grain, source `hw_output` also tiled at sub-MEM grain within each invocation (measured worse at scale — see [CLOCKWORK.md](CLOCKWORK.md)) |

Companion app-harness changes so host buffer sizes track `in_img`:
- `process.cpp` — allocates `Buffer<uint8_t>(CONV_IN_IMG, CONV_IN_IMG)` / output
  `(CONV_IN_IMG - CONV_KSIZE + 1)²`, defaulting to 64/3.
- `Makefile` — forwards `CONV_IN_IMG` / `CONV_KSIZE` into `CXXFLAGS` when defined.

### Note on non-symmetric input/output rewrite
A fully symmetric input/output rewrite (`input_glb`, `input_cgra` + `hw_output` tiled
at MEM) was attempted and hit clockwork-side constraints ("No viable banking strategy
for input_cgra_stencil", "Cannot select flush From output_glb…ubuf"). `conv2D_fp` uses
that pattern but is authored end-to-end to fit clockwork's ubuffer-topology
expectations; grafting it onto `conv_3_3` breaks the assumptions. The generator keeps a
named `output_glb` intermediate (inlined by default) as the minimal viable hook.

## Build / run

The Halide compiler library must reflect these src changes. The built
`distrib/lib/libHalide.a` was already newer than the changed `src/*.cpp`, so the flow
uses the intended behavior without a rebuild; if `src/` is edited, rebuild the distrib
before running. A run:

```bash
cd /aha/Halide-to-Hardware/apps/hardware_benchmarks/tests/conv_3_3
HALIDE_GEN_ARGS="in_img=64 schedule=3 mem_x=62 mem_y=31 unroll=3" CONV_IN_IMG=64 CONV_KSIZE=3 \
  aha halide tests/conv_3_3 --log --stop-after-clockwork
# latency + gold in log/aha_map.log and bin/map_result/conv_3_3/cgra_resource_estimation.csv
```

For image sizes other than 64 the compare step needs an `input.png` of at least
`in_img × in_img` (the app ships 64×64; a 258×258 synthetic PNG was used for the 256²
runs, then restored).

## Uncommitted / in-flight state
All six changed files are committed in `7d6dc01a8`. No H2H source is left uncommitted;
per-app `bin/` build artifacts are untracked as usual.
