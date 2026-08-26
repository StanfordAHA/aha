# /aha experiments — MEM-tile split-mem / Path B / thesis PD work

This directory documents the cross-repo changes made in the
Halide-to-Hardware → Clockwork → CGRA (garnet/lake) toolchain during the
`conv_3_3` split-mem latency investigation and the associated MEM-tile
thesis physical-design / power effort. Each subrepo is a separate git repo
(submodule of `/aha`); the notes here are the distilled, durable record of
what changed in each and why.

## Documents

| doc | subrepo | branch | what it covers |
|---|---|---|---|
| [CLOCKWORK.md](CLOCKWORK.md) | `clockwork` | `ready_valid_extract` | MEM-codegen fixes (fetch-width padding, NULL-safe affine extraction, sram2tb step-cap, GLB-metadata guards) + the full split-mem / Path B / 2-level latency investigation |
| [HALIDE-TO-HARDWARE.md](HALIDE-TO-HARDWARE.md) | `Halide-to-Hardware` | `max` | HW-xcel / add_kernel dedup, wrapper schedule inheritance, and the parameterized `conv_3_3` generator (schedules 0–4) |
| [LAKE.md](LAKE.md) | `lake` | `THESIS` | MEM-tile spec / collateral generation, lake↔clockwork round-trip RTL sim validation, PD power-test flow, dynamic SRAM columns |
| [GARNET.md](GARNET.md) | `garnet` | `modern_gf` | per-spec MemCore RTL through the mflowgen PnR/power flow, sweep harness, Tile_MemCore floorplan + spec-aware SRAM macro |

## The through-line

A naive split-mem `conv_3_3` schedule pays a **3.55×** latency penalty
(14535 vs 4095 cycles) because clockwork serializes the MEM sub-tiles through
the pipeline. **Path B** (tile the accelerator wrapper at MEM grain, one
synchronous accelerator invocation per sub-tile) recovers the baseline
(4222 cyc, 3.44× better) and is the only variant that is **RTL-realizable** on
the standard Amber MEM tile. 2-level nesting re-imports the penalty and
overflows the 11-bit MEM cycle counter, so it does not pay off even at 256².

The **RTL-realizability** result came from the lake↔clockwork round-trip
(VCS/xrun): split-mem/2-level per-tile SRAM controllers need agg2sram/sram2tb
data-path strides ≥2, but the wide-fetch datapath's stride register is 1-bit
(contiguous fetch only) — an architectural limit of the MEM tile, not a
compiler bug. See [LAKE.md](LAKE.md).

## Branch / commit state (as of this writing)

| repo | branch | key commit | pushed to origin? |
|---|---|---|---|
| clockwork | `ready_valid_extract` | `a80dfa20` | yes (fast-forward) |
| Halide-to-Hardware | `max` | `7d6dc01a8` | yes (new branch) |
| lake | `THESIS` | `897f96f1` (+ uncommitted) | branch is upstream; see LAKE.md |
| garnet | `modern_gf` | `8b4e56da` | branch is upstream; see GARNET.md |
| `/aha` (parent) | `mek` | gitlink bump commit | pins clockwork + H2H at the commits above |

The parent `/aha` repo (branch `mek`) pins each subrepo commit via submodule
gitlinks. A `git submodule update` would move a subrepo back to the pinned
commit — bump the gitlink after advancing a subrepo branch.

> Operational note: the standalone build machine runs garnet/lake from a
> separate checkout (`/sim/mstrange/BUILD_CGRA/…`) updated by direct `git pull`,
> not by `/aha` gitlink bumps. Fixes that must run there have to be pulled
> directly. See [GARNET.md](GARNET.md).
