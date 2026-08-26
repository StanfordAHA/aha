# `lake` on the `THESIS` branch — engineering reference

## Overview

The `lake` subrepo (`/aha/lake`) generates the CGRA MEM-tile (streaming
memory) hardware for the Halide-to-Hardware → Clockwork → CGRA toolchain.
Its `THESIS` branch is the working branch for a MEM-tile thesis / research
effort. Relative to `master` it adds three broad capabilities that plain
Lake does not have:

1. **A per-spec physical-design (PD) flow** under `pd/thesis/` that pushes a
   single Lake spec's MEM-tile RTL through synthesis → PnR → PrimeTime power,
   and — the newest, still-uncommitted work — produces **idle** and **active**
   power numbers at both the synthesis and gate (post-PnR) levels.
2. **A lake ↔ clockwork round-trip validation flow**: feed a spec's own
   `lake_collateral.json` into the clockwork compiler, take each per-tile
   memory config that comes back, regenerate the four sim artifacts, and
   verify the config actually executes on that spec's RTL. This turns
   spec/compiler/converter mismatches into build failures instead of silent
   miscompiles.
3. **Spec / collateral / SRAM-macro robustness fixes** discovered by driving
   real geometries (dual-port SDPB macros, narrow-word column counts,
   fw=1/regfile paths, dw=8/dw=64 corners) through those two flows.

A thesis-artifact pipeline (`THESIS/`, `ASPLOS_EXP/`) that turns build outputs
into LaTeX figures/tables is also on the branch but is largely orthogonal to
the MEM-tile hardware changes and is only summarized here.

> Note on sourcing: every mechanism below is grounded in current repo content
> (commit diffs, source files) except the two items flagged **[from session
> memory]**, which are distilled from cross-session notes under
> `/root/.claude/projects/-aha/memory/` and, where possible, corroborated
> against code that is actually present on the branch. Those notes are weeks
> old; treat their file:line citations as approximate.

---

## Branch & provenance

| Item | Value |
|---|---|
| Branch | `THESIS` (`git -C /aha/lake branch --show-current`) |
| HEAD | `897f96f1` — *"lake: dynamic SRAM column count with cols=2 default, cols=1 fallback"* |
| Merge-base with `master` | `aa3fc1a2` |
| Divergent commits | **34** (`aa3fc1a2..THESIS`) |
| Upstream | tracks `origin/THESIS` (StanfordAHA/lake) |

The commit history is a mix of true thesis work and earlier
`new_asplos_opt_rv_rd` merges that were carried onto the branch. Several older
commits touch `lake/modules/arbiter.py` and `lake/spec/*.py` for reasons
unrelated to the thesis PD/round-trip flow; the thesis-relevant clusters are
grouped by theme below.

There is also live uncommitted work on top of HEAD (see
[Uncommitted / in-flight state](#uncommitted--in-flight-state)).

---

## Theme A — Spec / collateral generation for MEM-tile variants

**What changed.** The `Spec` class (`lake/spec/spec.py`) grew the machinery to
(a) emit a compiler-facing description of the generated hardware and (b) accept
a clockwork tile config back and turn it into a bitstream. Key additions
(commits `e50caaaa`, `3536a143`, `9df62d50`, `853fc8e3`, `c0ca4628`,
`b2b295ec`, `3f877335`):

| Function (`lake/spec/spec.py`) | Role |
|---|---|
| `extract_compiler_information` (line ~1121) | Emits the collateral dict the compiler needs — includes `store_latency` / `load_latency` per hierarchy, iteration domains, controller names. |
| `_synthesize_wide_fetch_hierarchy` (line ~1030) | Builds the AGG→SRAM→TB wide-fetch hierarchy. **[from session memory]** sets external-interface `store_latency`/`load_latency` = 0 because the wide-fetch path absorbs SRAM macro latency internally; reporting the raw macro latency made clockwork over-stagger fw=2 SP multi-out. |
| `_is_clockwork_format` (line ~1882) / `_convert_clockwork_to_port_config` (line ~1892) | Recognize a clockwork tile JSON and convert its `in2agg_*`/`agg2sram_*`/`sram2tb_*`/`tb2out_*` (or `mem_*`, `in2regfile_*`/`regfile2out_*`) keys into a Lake port config. |
| `gen_bitstream` (line ~2155) | Turns a port config (or clockwork tile) into the packed config integer; `over=True` skips the internal clockwork-conversion step when the caller already converted. |

`lake/utils/generate_collateral.py` (new, commit `3536a143`) provides a
`build_mem_level_spec()` + `main()` entry point that writes the collateral
file to disk; `tests/spec_unit_tests/test_extract_compiler_information.py`
(new) exercises the extraction.

**Register-overflow guard** (`lake/spec/component.py`, ~line 245). A
value-range check was added to config-register packing: if a schedule value
clockwork emits exceeds the spec register width (`value > (1<<width)-1`) it now
raises a `ValueError` naming the register and telling the user to re-spec with
a wider `max_sequence_width`/`max_extent` or compile against a
pattern-compatible app — instead of silently truncating via `value & bmask`.
This guard is what surfaces the architectural limit documented in
[Key finding](#key-finding--split-mem--2-level-controllers-are-not-encodable-on-the-standard-amber-mem-tile).

---

## Theme B — Lake ↔ Clockwork round-trip compile + sim validation

**Goal.** For a given spec, prove the full loop: `lake_collateral.json` →
clockwork compile (`conv_3_3`) → per-tile JSON →
`_convert_clockwork_to_port_config` → `gen_bitstream` → VCS/xrun sim of
`lakespec.sv` → `Test PASSED!`. Progress and results live in
[`THESIS_ROUNDTRIP_PROGRESS.md`](../lake/THESIS_ROUNDTRIP_PROGRESS.md)
(as of 2026-05-08: **98/100 sweep configs pass**; the two failures are
structurally-invalid sweep cells the flow correctly rejects, not flow bugs).

**Core new module.**
[`lake/utils/clockwork_roundtrip.py`](../lake/lake/utils/clockwork_roundtrip.py)
(commit `25a9c33b`). Single public entry point
`write_roundtrip_artifacts(spec_factory_kwargs, tile_clockwork_json_path,
output_dir)` — the inverse of the collateral path. Given the same spec kwargs
that built the collateral plus one tile's clockwork config, it writes the four
files the RTL-sim harness expects into `inputs/` (and `inputs/gold/`):

- `bitstream.bs` — from `spec.gen_bitstream(port_config, over=True)`.
- `gold/port_rN_{data,time}.txt` — computed by `_compute_clockwork_gold`,
  which models the Lake hierarchy as a flat FIFO (input port writes
  `0,1,2,…`; each output port drains in its `tb2out_`/`mem_out_`/`regfile2out_`
  schedule order). Two correctness subtleties baked in:
  - **`load_latency` offset** applied only to the fw=1 `regfile2out_`/`mem_out_`
    paths (their `cycle_starting_addr` is the read-*fire* cycle; data lands
    `load_latency` cycles later). Wide-fetch `tb2out_` already encodes the
    data-out cycle. `load_latency` is read back from
    `spec.extract_compiler_information()` so the helper stays in sync.
  - **data masked to `data_width`** (`i & ((1<<data_width)-1)`) — real HW
    truncates, so an unmasked `range(N)` mismatched HW for dw<16 past index 256.
- `comp_args.txt` — `+define+CONFIG_MEMORY_SIZE/NUMBER_PORTS/DATA_WIDTH`.
- `PARGS.txt` — per-port data sizes from `get_data_sizes` plus
  `max_time`/`static`.

Failures are returned in-band (`{"status": "...","error": ...}`) rather than
raised, so a caller can keep iterating across tiles.

**mflowgen scaffolding** (all under `pd/thesis/`, commit `25a9c33b`):

| Step dir | Purpose |
|---|---|
| `clockwork-roundtrip-compile/{configure.yml, run_clockwork.py}` | Compiles conv_3_3 against `lake_collateral.json`, walks the CoreIR JSON, splits each `cgralib.Mem_amber` instance's config into per-tile `tile_<idx>.json` (keys the converter accepts). Non-zero exit if no tiles emit. |
| `clockwork-roundtrip-common/{Makefile, run_roundtrip_sim.py, run_sim.tcl, test_comparison.py}` | Shared per-tile driver: stage `cfg_<idx>/`, call `write_roundtrip_artifacts`, `make sim`, parse PASS/FAIL, accumulate `roundtrip_results.json`. |
| `clockwork-roundtrip-sim-rtl/configure.yml`, `clockwork-roundtrip-sim-synth/configure.yml` | RTL-level and synth-netlist-level variants of the round-trip sim. |
| `tests/test_spec/test_clockwork_roundtrip.py` | pytest smoke for `write_roundtrip_artifacts` against a synthetic tile JSON. |

`run_clockwork.py` wraps `aha.util.sweep_thesis_collateral.run_clockwork_compilation`;
`clockwork_roundtrip.py` imports `build_spec` from
`aha.util.sweep_thesis_collateral`, i.e. this flow reaches back into the `aha`
driver to build the same spec the sweep does.

**Bugs this flow caught** (per `THESIS_ROUNDTRIP_PROGRESS.md`): fw=2
lake-vs-clockwork stride mismatch, fw=2 SP multi-out double-firing, fw=1 DP
large-`sc` extent-encoding overflow, dw=8 testbench cycle-counter wrap (real,
not round-trip-specific), dw=8 gold-data wrap mismatch, `get_data_sizes`
empty-`vec_in_config` crash, and multi-port bank-merge gating. Several of the
fixes landed in `clockwork/`, not `lake/` — that half is documented there.

---

## Theme C — PD flow: synthesis → PnR → power

**What it is.** `pd/thesis/` is the canonical mflowgen design definition. One
copy serves *all* sweep configs; per-config values are injected via
`--graph-kwargs` at graph-generation time (`clock_period`, `storage_capacity`,
`data_width`, `fetch_width`, `dual_port`, `python_command`, `test_dir`). Full
step-by-step in [`pd/thesis/README.md`](../lake/pd/thesis/README.md); the
graph is built by `pd/thesis/construct-commercial-full.py`. Landed as the large
commit `4ca488d3` (rtl, constraints, gen_sram_macro, cadence-innovus-init/
signoff, synopsys-ptpx-synth/gl, synopsys-vcs-sim-rtl, testbench, etc.).

**How to run** (from `pd/thesis/README.md`):

```bash
# One config, up through synthesis:
mflowgen run --design /path/to/lake/pd/thesis --graph-kwargs "{...}"
make list | grep cadence-genus-synthesis   # find step N
make N

# Full sweep, parallel:
python ASPLOS_EXP/run_synth_pool.py --build-dir /sim/mstrange/THESIS_BUILDS --jobs 8 --phase both
```

**Existing power paths (committed).** The graph wires two `vcd2saif` chains:
an RTL-sim VCD → `synopsys-ptpx-synth` (synth-level power, no PnR) and a
post-signoff GLS VCD → `synopsys-ptpx-gl` (post-PnR power with SPEF). The
RTL-VCD path is gated on `+dump_vcd=1`, off by default so pass/fail sweeps
don't pay multi-GB VCD costs (`ASPLOS_EXP/run_power_flow.sh` flips it on).
There are also round-trip-fed power nodes (`pt_power_roundtrip_rtl/synth`).

**Idle vs active power (largest new capability — UNCOMMITTED).** See
[Uncommitted / in-flight state](#uncommitted--in-flight-state); the generator
is `pd/thesis/power-test-gen/gen_power_bitstreams.py`, which produces two
bitstreams (idle, active) from the *same* spec kwargs the rtl step uses.

**SRAM macro selection.** `construct-commercial-full.py` computes the GF12 SRAM
macro from `storage_capacity`/`data_width`/`fetch_width` via `GF_Tech_Map`
(`lake/top/tech_maps.py`) and parameterizes `gen_sram_macro`. Only
`W01024B064` (1024×64, 8 KB single-port) is confirmed available in the ADK per
the README — other geometries fail at `gen_sram_macro`.

**Generic (no-ADK) synth→power path** (untracked dir
`pd/thesis/generic-synth-power/`, documented in
[`GENERIC_SYNTH_POWER.md`](../lake/pd/thesis/generic-synth-power/GENERIC_SYNTH_POWER.md)).
Self-contained Genus/DC + a generic 45 nm `.lib` + PrimeTime idle/active power,
with **no gf12 ADK / macros / PnR**. It reuses the real flow's constraint
recipe verbatim (`config_memory*` false-path, flush multicycle 10/9, driving
cell, load, fanout, max-transition) — only the clock period is caller-supplied.
Storage is behavioural flops (`physical=False`), so numbers are **relative**,
not tapeout-accurate. Driver `generic_synth_power.sh`; a companion
`fmax_sweep.sh` does synthesis-only Fmax characterization (sweeps clock
targets, derives `Fmax = 1/(target − worst_slack)`, with `--io-delay-frac 0`
for internal-logic Fmax). Two PrimeTime gotchas are baked in: `current_design`
must precede `link`, and a Genus-written `.sdc` must not be `read_sdc`'d
(embedded `current_design` line silently drops the clock).

---

## Theme D — Idle / active power-test bitstream generator

`pd/thesis/power-test-gen/gen_power_bitstreams.py` (untracked; wired in by the
uncommitted `construct-commercial-full.py` edit) builds two bitstreams for one
spec so downstream power analysis has a **min/max bracket** rather than a
single mid-loaded number.

- **Idle** — application `{'constraints': []}`. `gen_bitstream` calls
  `clear_configuration()` then iterates zero ports, so the DUT loads a cleared
  config and sits still. (Session memory: hex len = 1 / value 0 for the default
  4-port fw=4 spec.)
- **Active** — `build_active_application` schedules every port with linear
  address strides and holds valids/readies high. Crucially it **phase-shifts on
  single-port specs**: writes on even phases (`stride=2, offset=2+2·i`), reads
  on odd phases (`stride=2, offset=3+2·j`), so the shared RW SRAM port is never
  starved. Dual-port specs fire every cycle (`stride=1`) since R and W have
  dedicated ports. This fixed an earlier bug where `stride=1` on a single-port
  spec completed only ~4/1000 reads due to RW-port contention.

PARGS carry `+wN_num_data`/`+rN_num_data` (0 for idle, `sim_cycles` for
active), `+static=1`, `+max_time`, and `+power_only=1`. The last bypasses the
shared testbench's end-of-run count checks, which are meaningless for power
tests (active deliberately overruns what the DUT can service). The spec is
built once via `tests/test_spec/thesis_sweep.build_four_port_wide_fetch`
(loaded by path, so it runs from any CWD) and `generate_hardware()` is called
before `get_total_config_size()`/`get_num_ports()`.

---

## Theme E — Power-test VCD validator

**[from session memory]** A signal-category VCD validator was built to confirm
the idle/active bitstreams actually do what they claim — necessary because
`+power_only=1` disables the tb.sv PASS/FAIL check, so a broken active
bitstream would otherwise still emit a meaningless "power number."

- **Idle assertion:** every data-path signal changes ≤ 10 times after config
  load (nothing on the data path moves).
- **Active assertion:** SRAM address bus and SRAM data bus each accumulate
  ≥ 50 total value changes (the workload really touches memory). `port_*_valid`
  /`ready` and `mem_intfdec_en` are deliberately *not* used (held static under
  `+static=1`, or unreliable across SP/DP). A DUT-presence check (`total
  datapath signals > 0`) fails early when the port config isn't in the VCD
  (`tb.sv` only has generate cases for `NUMBER_PORTS ∈ {2,4,8}` → 1×1/2×2/4×4).

> Caveat: per the memory note the validator itself
> (`validate_sim.py`) and its driver (`run_spec.sh`) live under
> `/aha/sweep_out/power_tests_*`, i.e. in the **ephemeral sweep-output tree,
> not committed inside the `lake` repo**. I could not find them under
> `/aha/lake`; treat this validator as flow tooling that accompanies the branch
> rather than part of the branch's tracked source.

---

## Theme F — Dynamic SRAM column count (commit `897f96f1`, current HEAD)

The GF tech map previously hardcoded `sram_columns=2` (each word split across
two half-width macros). Narrow-word geometries have no 2-column macro — e.g.
fw=2 / dw16 / sc2048 gives `mem_width=32, depth=512`; two 16-bit columns need
`depth≥1024`, so `GF_Tech_Map` aborted with *"No valid macros."*

`CoreCombiner._select_gf_tech_map()` (new, `lake/top/core_combiner.py`) now
**searches** the column count: it enumerates divisors of `mem_width`, tries
`cols=2` first (preferred), then falls back to `cols=1` (one full-width macro)
and upward, catching each `GF_Tech_Map` `AssertionError` until one succeeds,
and sets `self.sram_columns` accordingly.

- **Why cols=2 default:** splitting keeps each macro narrower/shorter, which
  matters because the MemCore tile has a **fixed height in PnR** (it must abut
  PE tiles) — a single full-width macro can overflow that height. It also keeps
  every already-valid geometry **byte-identical** to previously validated RTL.
- **cols=1 fallback** handles the narrow fw=2 case (fits as one 32-bit
  `W00512B032` macro).
- Verified via a local RTL-gen sweep of all 6 `DEFAULT_SPEC_POINTS`: 5 macros
  unchanged, fw2_sc2048_sp fixed, all 6 emit `garnet.v`.

`PhysicalMemoryStub` (`lake/top/memory_interface.py`) lays `cols` macros side
by side, broadcasting the word address and splitting the data.

---

## Theme G — Dual-port (SDPB) spec RTL fix (commit `8bc6995f`)

Dual-port spec MemCores had never been exercised through the garnet lake-spec
RTL path; three single-port assumptions crashed `garnet.py` RTL gen for the
`fw2 dual-port` sweep config. A dual-port spec (`dual_port=True` →
`rw_same_cycle`) builds a `[RW, R]` logical port list and must map onto the
SDPB 1rw1r macro (two port maps). Fixes:

1. **`core_combiner`** built the tech map without `dual_port` → single-port
   S1xB map (1 port) → R port indexes `port_maps[1]` → `IndexError`. Now
   `_select_gf_tech_map` passes `dual_port=self.rw_same_cycle` so `GF_Tech_Map`
   returns the SDPB map. (This code path was subsequently folded into the
   `897f96f1` column-search rewrite.)
2. **`memory_interface.py` `PhysicalMemoryPort.create_port_interface`** READ
   branch knew only `data_out`/`read_addr`; the SDPB read map (`dual_port_p1r`)
   names them `read_data`/`addr` → `KeyError`. Added the same fallbacks the
   READWRITE branch already had.
3. **`PhysicalMemoryStub`** READ branch **concatenated** per-column child
   `read_addr`s into the parent (num_wide× too wide → width mismatch). The
   address is a shared word address → **broadcast** it like the READWRITE
   branch. Latent until a READ port with `num_wide>1`, which the dual-port
   macro is the first to hit.

Verified: fw2 (dp, dw16, sc4096, vec2) now emits
`IN12LP_SDPB_W01024B016M04S2_H` and `garnet.py` completes; single-port fw1
unchanged (`IN12LP_S1DB_W02048B008M16S2_H`).

> Cross-reference: the same tech-map/dual-port rules are captured in the branch
> `CLAUDE.md` §5 (which is itself part of the uncommitted diff, see below) and
> in the `garnet/mflowgen` sweep notes. Both note a flaky, non-deterministic
> coreir/kratos SIGSEGV (`rc=139`) in `garnet.py` past tech-map selection; the
> `aha` driver wraps garnet.py in `retry()`.

---

## Key finding — split-mem / 2-level controllers are NOT encodable on the standard Amber MEM tile

**[from session memory + corroborated by the `component.py` guard]**

When conv_3_3 is scheduled with a **split-mem** (schedule=1) or **2-level
nested** (schedule=4) Halide schedule, the input GLB tiles pass RTL sim, but
the **sub-tile SRAM controllers** (the per-tile `agg2sram_0` / `sram2tb_0`
memories) **fail at bitstream generation** — they trip the register-overflow
guard in `lake/spec/component.py` (~line 253 in the note, the
`value > (1<<width)-1` `ValueError`).

The reason is architectural, not a compiler bug:

- These sub-tile controllers need **data-path (AGG→SRAM / SRAM→TB) strides ≥ 2**
  (observed dimension strides 2 / 7 / 19) and **starting addresses ≥ 14**.
- The standard Amber wide-fetch MEM-tile datapath encodes only **contiguous
  fetch**: its per-dimension AGG/TB data-path stride register is effectively
  **1 bit** (stride ∈ {0,1}) and its `starting_addr` field is **~3 bits**.
- So a schedule whose *data-path* access is strided or offset beyond those
  fields simply cannot be programmed onto the tile.

Further properties from the investigation: it is **independent of fetch-width
alignment** (an aligned `mem=8` case fails the same as `mem=31`); the
`max_extent` / `max_sequence_width` spec knobs **do not help**, because they
widen the AddressGenerator / IterationDomain registers, *not* the AGG/TB
data-path stride registers. At larger image sizes the 2-level schedule also
overflows the 11-bit MEM cycle counter (its cumulative inner-sub-tile offsets
reach 17-bit `cycle_starting_addr` values) and runs ~3.2–3.6× *slower* than the
line-buffered single-level schedule.

**Conclusion:** split-mem / 2-level per-tile SRAM controllers can only be
realized on a MEM tile with **wider AGG/TB data-stride registers** — a
hardware-spec change, not a compiler change. Among the conv_3_3 schedules
studied, the "Path B strip" schedule (schedule=3) is the one that both runs on
the existing hardware and is ~3.4× faster. This is precisely the kind of
finding the round-trip RTL flow (Theme B) exists to surface: without it the
mismatch would have looked like a green compile.

Full detail lives in the cross-session note
`/root/.claude/projects/-aha/memory/project_conv_3_3_split_mem_clockwork.md`
and in `clockwork/CLAUDE.md`.

---

## Uncommitted / in-flight state

`git -C /aha/lake status` on `THESIS` shows the following **not yet committed**
on top of HEAD `897f96f1`:

**Modified (tracked):**

| File | Change |
|---|---|
| `CLAUDE.md` | Adds §5 *"Spec MemCore RTL generation (the garnet lake-spec sweep)"* — documents `_select_gf_tech_map` (cols=2/cols=1 rules), the three dual-port bugs (`8bc6995f`, `897f96f1`), and the flaky garnet SIGSEGV. Also registers the `generic-synth-power` doc in §2/§3. |
| `pd/thesis/construct-commercial-full.py` | Adds the **idle/active power infrastructure** to the mflowgen graph: a `power-test-gen` node; two `synopsys-vcs-sim-power` clones (`idle`/`active` via a `variant` param); per-variant `vcd2saif` → `synopsys-ptpx-synth` chains (**synth-level** idle/active power); and a full **gate-level** mirror (`synopsys-vcs-sim-power-gl` on the routed signoff netlist + SDF → `vcd2saif` → `synopsys-ptpx-gl` with signoff SDC/SPEF) for real post-layout idle/active numbers. Forwards spec kwargs (incl. `sim_cycles`) to `power_gen` and wires variant-suffixed bitstream/PARGS files to each sim's generic input names. |

**Untracked directories under `pd/thesis/`:**

| Dir | Contents / purpose |
|---|---|
| `power-test-gen/` | `gen_power_bitstreams.py` (Theme D) + `configure.yml` — the idle/active bitstream + PARGS generator the graph edit above consumes. |
| `synopsys-vcs-sim-power/` | `Makefile`, `configure.yml`, `run.sh`, `run_sim.tcl`, `tb.sv` — RTL-level power sim step (variant-labeled; `DUMP_VCD=1` default; no gold/compare). |
| `synopsys-vcs-sim-power-gl/` | Same five files — **gate-level** power sim step: simulates the routed signoff netlist with SDF back-annotation. |
| `generic-synth-power/` | `generic_synth_power.sh`, `fmax_sweep.sh`, `GENERIC_SYNTH_POWER.md` — the no-ADK 45 nm synth→power / Fmax path (Theme C). |

> The idle/active power flow is therefore **functional but uncommitted**: the
> graph wiring (`construct-commercial-full.py`), the bitstream generator, and
> both sim step dirs are all present in the working tree but not in any commit.
> Session memory reports it was validated at RTL level (idle+active both sim
> clean; active SAIF switching ~3.6× idle) but the full synth+power numbers
> were deferred to a longer-budget run.

**Not in the `lake` tree at all:** the VCD validator (`validate_sim.py`) and
its `run_spec.sh` driver live under `/aha/sweep_out/power_tests_*` (ephemeral
experiment output), not inside this repo — see Theme E caveat.

---

## Pointers

- [`THESIS_ROUNDTRIP_PROGRESS.md`](../lake/THESIS_ROUNDTRIP_PROGRESS.md) — round-trip status, per-config PASS/FAIL matrix, per-bug root causes.
- [`pd/thesis/README.md`](../lake/pd/thesis/README.md) — mflowgen design definition, parameter flow, run recipes.
- [`pd/thesis/generic-synth-power/GENERIC_SYNTH_POWER.md`](../lake/pd/thesis/generic-synth-power/GENERIC_SYNTH_POWER.md) — no-ADK synth→power / Fmax path.
- `lake/CLAUDE.md` §5 — spec MemCore RTL generation / tech-map rules (currently uncommitted).
- `THESIS/PIPELINE.md`, `THESIS/REPLICATION.md` — thesis-artifact pipeline and end-to-end PD replication (orthogonal to the MEM-tile hardware changes here).
