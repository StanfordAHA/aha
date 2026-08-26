# Clockwork changes — split-mem / large-tile MEM codegen

Documentation of the modifications made to the `clockwork` subrepo (`/aha/clockwork`)
in support of multi-level (split-mem / Path B / 2-level) Halide schedules for the
`conv_3_3` hardware benchmark, and the investigation those changes came out of.

Companion docs: [HALIDE-TO-HARDWARE.md](HALIDE-TO-HARDWARE.md) (the H2H-side compiler
fixes and the conv_3_3 generator that drives these schedules), [LAKE.md](LAKE.md)
(MEM-tile spec / RTL realizability), [GARNET.md](GARNET.md) (fabric + PnR).

## Branch & provenance

| | |
|---|---|
| Repo | `/aha/clockwork` (submodule of `/aha`, url `StanfordAHA/clockwork`) |
| Branch | `ready_valid_extract` |
| Base | `36b5bcc4` (`update rv extract for roudn trip compilation`) — the upstream tip this work sits on |
| Our commit | `a80dfa20` — "Enable split-mem / large-tile conv schedules through MEM codegen" |
| Files | `isl_utils.cpp`, `isl_utils.h`, `ubuffer.cpp`, `coreir_backend.cpp` |

The commit is a clean fast-forward on top of the upstream `ready_valid_extract`
branch tip. It does **not** include `build_set_test.cpp` (which carries session-only
debug `cout` instrumentation) nor the local `CLAUDE.md` session notes — those remain
uncommitted in the working tree by design.

## The problem being solved

The `aha halide tests/conv_3_3` flow lowers a Halide schedule to a clockwork `prog`,
which clockwork compiles to per-op MEM-tile controllers (`compile_mem` /
`--stop-after-clockwork`) and, via the metamapper, to a full CGRA placement (`make map`).
Several multi-level schedules that are *functionally correct* (Halide-CPU and
clockwork functional sim agree, gold=1) failed to **compile to MEM controllers**
because of latent assumptions in clockwork's codegen path:

1. Schedules where `mem_x % fetch_width != 0` produced a multi-valued agg→SRAM
   access *relation* that the single-affine extractor rejected.
2. Split-mem / 2-level topologies have only one externally-addressed GLB (the input
   load); GLB-metadata emission hardcoded lookups that assume a separate
   output-direction GLB tile, and threw `std::out_of_range` / `json out_of_range`.
3. Large single-level tiles (e.g. `conv_3_3` at 256²) blew an arbitrary iteration
   cap in the sram2tb delay search.

Each fix below is guarded so that previously-working apps are byte-identical.

## Fix 1 — `pad_addr_dim_to_fetch_width` + NULL-safe affine extraction (`isl_utils.cpp/.h`)

**Symptom.** For `mem_x % fetch_width != 0` (default `fetch_width = 4` from lake
collateral), the agg→SRAM access map takes the form
`agg[..., o1] : o1 mod 4 = 0 ∧ base-4 ≤ o1 ≤ base` — a *relation*, not a function —
because isl cannot symbolically simplify `floor((non-multiple-of-fw · affine)/fw)`.
`get_aff()` then finds no single affine and the compile aborted (originally via a
NULL forwarded into `str(nullptr)`).

**Fix.**
- New helper `pad_addr_dim_to_fetch_width(isl_map* m, int addr_dim, int fetch_width)`:
  pads the addr-dim affine's input-dim coefficients up to a multiple of
  `fetch_width`, so the subsequent `floor`-by-fetch_width slice simplifies to a
  clean affine. Re-attaches the original domain via `isl_map_intersect_domain` so
  downstream LP solvers still see bounded variables. Returns the input unchanged if
  the map is multi-valued, multi-piece, or already aligned. Prototype added to
  `isl_utils.h`.
- `simplify_expr` / `simplify` now try `isl_map_coalesce` when
  `isl_pw_multi_aff_from_map` returns NULL, and return the (coalesced) input rather
  than forwarding NULL.
- `get_aff` / `get_multi_aff` try coalescing on NULL, and otherwise **throw a
  diagnostic `std::runtime_error`** ("multi-valued map not supported", with the map
  printed) instead of asserting on NULL. This turns a silent abort into an
  actionable error.

**Where it fires.** `ubuffer.cpp`'s `get_vectorized_write`, just before the
`dot(acc_vec, slice)` (see Fix 3). The hardware can already run such schedules
(4-port AGG with per-port addressors); only this codegen path lacked per-port
decomposition, and padding sidesteps it.

## Fix 2 — guarded GLB-metadata lookups + earliest-start host2glb (`coreir_backend.cpp`)

Three related sites assumed a two-GLB (input + output) topology. Split-mem
(`schedule=1`) and 2-level (`schedule=4`) conv_3_3 have exactly **one** externally-
addressed GLB — the input load — so the output-direction map (`cgra2glb`) is empty.

- **`addIOsWithGLBConfig` / `addIOsWithGLBConfigMetaMapper`.** The overrides
  `glb_metadata->glb2cgra.at(key)` / `cgra2glb.at(key)` are now guarded with
  `count(key)` checks; when the key isn't registered, the IO keeps the
  `in_buf/out_buf.config_file` metadata already assigned, with a one-line
  diagnostic. The output-side key extraction `split_at(buf_name,"_").at(1)` is also
  bounds-guarded. (This unblocked the `compile_mem` / `--stop-after-clockwork` path.)

- **`ReplaceGLBValid::runOnInstance` (~line 4601).** Previously did
  `valid_config.at("output")` with a hardcoded `"output"` key. `valid_config` is the
  `cgra2glb` json whose keys are `pick(split_at(buf,"_"))` (first token, e.g.`"hw"`),
  never literally `"output"` for conv_3_3-style names. For s1/s4 `cgra2glb` is empty
  and `latency != 0`, so the pass ran past its early-return → `json out_of_range`.
  Now: use `"output"` if present; else if there is a single `cgra2glb` entry use it;
  else log and `return false` (skip the stencil_valid replacement). This unblocked
  the **metamapper `make map`** path. The skip is correct by construction — the pass
  exists only to compensate an output routed through a *multi-tile* GLB, which s1/s4
  do not have, so the pre-existing single-tile output-valid config is already right.

- **host2glb latency selection (~line 2765).** `host2glb_latency` is derived from
  the host→GLB input load. It used to be selected by `starting_cycle == 0`. With
  deeper schedules (e.g. `schedule=4` at 128²) the input GLB's first activity is at a
  small nonzero pipeline offset (`starting_cycle == 2`), so the `== 0` gate missed
  it, `host2glb_latency` stayed 0, and `host2glb_optimization` asserted
  `host2glb_latency != 0` (`ubuffer.cpp:4910`). Fix: compute `min_glb_start` over all
  glb buffers and select the input load by `starting_cycle == min_glb_start`.
  Byte-identical to the old `== 0` whenever the input starts at 0 (all previously-
  working apps); tolerant of a pipeline offset otherwise.

## Fix 3 — sram2tb step-cap raised (`ubuffer.cpp`)

`search_for_sram2tb_schedule` finds the sram2tb read delay by repeatedly shifting the
temp schedule by −1 until it no longer violates the agg2sram write / sram2tb read
dependencies. The loop was capped with `assert(step < 100)`.

**Symptom.** The required delay is O(tile-schedule-span); for large tiles it exceeds
100 and the assert aborted. Observed for `conv_3_3` at 256² on **every** single-level
Path B grain tried (256×128, 256×64, 64×64) — gold-compare passed each time, so the
functional schedule was fine; only this controller-emission search over-shot the
arbitrary cap.

**Fix.** Raise to `const int STEP_CAP = 200000` (kept finite so a genuine
non-convergence still aborts loudly), with a one-line "step-cap>100 engaged" print
when it crosses 100. **Monotonic-safe:** only turns previously-aborting large configs
into successful compiles; any schedule that converged under 100 is unchanged. Also in
this file: the `pad_addr_dim_to_fetch_width` call in `get_vectorized_write` (Fix 1).

Regression-verified after rebuild: `conv_3_3` 62² single-level = 4095, 62² Path B
strip = 2111, both gold=1, and the ">100" message does not fire on small configs.

## Rebuild recipe

`clockwork_codegen` (the per-app driver binary) dynamically links
`lib/libclkwrk.so`, so only the shared lib needs rebuilding after a source change:

```bash
cd /aha/clockwork
source user_settings/aha_settings.sh   # sets BARVINOK_PATH, ISL_PATH, OPT_PATH, COREIR=1
export COREIR_PATH=/aha/coreir          # not set by the settings file
make libclkwrk.so -j$(nproc)            # recompiles the changed .o, relinks lib/libclkwrk.so (~123 MB)
```

Artifacts: `bin/map_result/conv_3_3/cgra_resource_estimation.csv` (top-line `latency`
+ max controller register values), `bin/mem_cout` (per-`Mem_amber` config dump).

## Investigation results these fixes enabled

### Split-mem latency penalty (the original motivation)
Single-level `conv_3_3` (whole 62² tile) runs at latency **4095**. A naive split-mem
schedule (`schedule=1`, mem=31, glb=62) runs at **14535** — a **3.55×** penalty. Root
cause: `adjust_outer_delays_sequentially` (`build_set_test.cpp:18917`) forces the
GLB-write to start only after the upstream MEM's *full* runtime
(`coarse_pipeline_II[producer] = sched.total_latency(producer)`), serializing all four
sub-tiles through the pipeline before the output MEM begins producing.

### Path B (schedule=3) is the fix
Tiling the accelerator **wrapper** at MEM grain (so each MEM sub-tile is its own
accelerator invocation, driven by a host-side loop of synchronous `RDAI_device_run`
calls) recovers near-ideal throughput: 62×31 strips → **2 invocations × 2111 = 4222
cycles**, matching the single-level baseline and beating the split-mem penalty by
**3.44×**. Path B is also the only variant validated on real MEM-tile RTL (see
[LAKE.md](LAKE.md) round-trip results).

### 2-level nesting (schedule=4) does NOT pay off at scale — measured at 256²
| config | invoc | per-invoc | **total** | max cyc_start_addr | mappable | cyc/px |
|---|---|---|---|---|---|---|
| s0 single whole-tile | 1 | 66563 | **66563** | 518 (9b) | ✓ | 1.02 |
| s3 Path B 256×128 strips | 2 | 33539 | **67078** | 518 (9b) | ✓ | 1.02 |
| s3 Path B 128×128 | 4 | 16899 | **67596** | 262 (8b) | ✓ | 1.03 |
| s4 2-level sub=64 | 1 | 212615 | **212615** | 147080 (17b) | ✗ | 3.24 |
| s4 2-level sub=128 | 1 | 234023 | **234023** | 168488 (17b) | ✗ | 3.57 |

(65536 output px; `mappable` = does the max controller `cycle_starting_addr` fit the
11-bit MEM cycle counter, `counter_ub = 2047`.) 2-level is **3.2–3.6× slower AND
unmappable**: `adjust_outer_delays_sequentially` serializes the inner sub-tiles inside
one invocation (the split-mem penalty resurfacing internally → ~3.2–3.6 cyc/px vs the
line-buffered ideal ~1.0), and their cumulative offsets push `cycle_starting_addr` to
17 bits, overflowing the counter. Single-level total is ~invariant to strip size
(work-conserving); smaller strips only shrink `cycle_starting_addr`. Conclusion:
single-level Path B (or a plain single tile) is the approach; nesting only re-imports
the penalty it was meant to remove.

## Related but still-open clockwork issues (not addressed here)
- **The serialization itself** (`adjust_outer_delays_sequentially`) is worked around
  by Path B, not fixed. A true fix would teach it to treat a flat consumer op with a
  small trip count relative to its producer as pipelined; likely regresses other apps
  unless carefully guarded. Alternatives explored (and why they were insufficient):
  the `_cgpl` variant swap dropped only ~130 cycles; `index_variable_prefetch_cycle`
  bypasses dependence analysis. See `/aha/clockwork/CLAUDE.md` for the full trail.

## Uncommitted / in-flight state (working tree, not in `a80dfa20`)
- `build_set_test.cpp` — session-only `[DIAG …]` / `[NSDIAG …]` `cout` traces; **excluded on purpose.**
- untracked `CLAUDE.md` — session notes (the authoritative long-form log; this file is a distilled export of it).
- untracked `OUTPUT_OVERLAP_FIX_PLAN.md` — an earlier planning note.
- build artifacts (`*.o`, `lib/libclkwrk.so`) — not tracked.
