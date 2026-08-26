# GARNET — the `modern_gf` branch

Engineering reference for the changes carried on the **`modern_gf`** branch of the
`garnet` subrepo (`/aha/garnet`), relative to `master`. `modern_gf` exists to
push **per-lake-spec MemCore RTL through the mflowgen physical-design flow**
(RTL → synth → place/CTS/route → signoff → power) on the GlobalFoundries 12 nm
(`gf12-adk`) process, driven by a **sweep harness** that builds one independent
mflowgen workspace per memory-tile specification. It is the garnet + mflowgen
half of a CGRA MEM-tile thesis effort; the lake half (how the per-spec RTL and
SRAM geometry are generated) is documented in the companion `LAKE.md` and in
`/aha/lake/CLAUDE.md`. The end product is comparable PPA/power numbers for a
family of MEM-tile spec variants (fetch width, SRAM capacity, port count,
single- vs dual-port), without disturbing the default (non-spec) onyx MemCore
build — the default path is verified to stay byte-identical.

> Every claim below is grounded in the branch's commits and files. Where a
> mechanism could not be fully verified from the repo, it is flagged
> **(unverified)**.

---

## Branch & provenance

| Item | Value |
|---|---|
| Branch | `modern_gf` |
| HEAD commit | `8b4e56da` — *"Tile_MemCore: add RTL-activity power level (ptpx-rtl) + --power all-3"* |
| Merge-base with `master` | `020c9b79` |
| Divergent commits | **32** (`020c9b79..modern_gf`) |
| Uncommitted tracked diffs | **none** (see *Uncommitted / in-flight state*) |

The bulk of the divergence lives under `mflowgen/`. A handful of early commits
also touch the RTL generator itself (`garnet.py`, `cgra/util_onyx.py`,
`memory_core/core_combiner_core.py`) to add the `--lake-spec-config` plumbing
and to make the build work against the GF process/container.

Commit themes (grouped from `git log --stat`):

- **RTL-gen / GF enablement:** `02ae2f18`, `0dedd8b1`, `66b179ca`, `901537da`
  (garnet.py `--lake-spec-config`, util_onyx spec parsing, GF build fixes).
- **Sweep harness (`sweep_specs.py`):** `3aefab56` (initial 401-line driver),
  `8986f11a`, `0de6527f`, `bfebd2dd`, `b32f5a7f`, `62ad6a37`, `09ef7a6c`,
  `14f3c8fb`, `85c4cf01`, `55f41a54`, `42a174d8`, `62ed114e`, `bc02d0d9`.
- **Containerized RTL build (`gen_rtl.sh`):** `1d8a816c`, `b8929f02`,
  `684b25e5`, `28928b70`, `4c76d298`.
- **Tile_MemCore spec-aware SRAM + constraints:** `1f28222f`, `82c8f706`,
  `d92fa948`.
- **Floorplan die-sizing:** `b290c3c8`, `26affa0c`, `3e729f78`.
- **Power flow (RTL-activity ptpx):** `8b4e56da`.
- **Helper scripts:** `ed560bd2` (`watch_step.sh`), `83803d91` (`logclip.sh`).

---

## (a) The sweep harness — `mflowgen/sweep_specs.py`

**What / why.** A standalone (stdlib-only) driver that sweeps a curated list of
lake-spec points through a garnet mflowgen build. It depends only on `mflowgen`
being on PATH and on this garnet checkout — it does **not** import lake, aha, or
the wider toolchain. Introduced in `3aefab56`; matured over ~a dozen commits.

**Spec points.** `DEFAULT_SPEC_POINTS` (lines 62–86) is six dicts over the axes
that actually move MemCore area/timing: `storage_capacity`, `data_width`,
`vec_width`, `in_ports`/`out_ports`, and `dual_port`. Each dict's stable name
comes from `_config_name()` (line 397), e.g. `fw4_dw16_sc8192_sp_in2_out2_vc2`
(`fw`=vec/fetch width, `sc`=capacity, `sp`/`dp`=single/dual port). The names are
deliberately aligned with the collateral sweeps in `aha`.

**Per-config flow** (`_run_one`, line 514):
1. Export knobs into the env: `LAKE_SPEC_CONFIG` (path to the spec JSON),
   `LAKE_SPEC_MODE` (`static`/`rv`), `DUAL_PORT`, `USE_NON_SPLIT_FIFOS`,
   `USE_SIM_SRAM`; plus `SYNTH_POWER`/`RTL_POWER` under `--power`.
2. `mflowgen run --design <graph>` in the per-config workspace.
3. Optional `make clean-*` (`--clean`/`--clean-all`).
4. **Write `spec_config.json` *after* the clean** (`85c4cf01`) — `make
   clean-all` wipes everything except `Makefile`/`.mflowgen*`, so writing it
   earlier would let clean-all delete it and break the rtl step. `mflowgen run`
   only needs the *path* (baked from the env), not the contents.
5. `make <stop-after>` (default `cadence-innovus-signoff`), then copy PPA-ish
   artifacts into `artifacts/` and append a row to `results.csv`.

**Key flags** (`build_argparser`, line 118):

| Flag | Effect |
|---|---|
| `--preset {smoke4,full}` | Named subsets of the spec list (`14f3c8fb`, `62ed114e`). `smoke4` = a diverse 4-config regression (single/multi controller, single/dual port, small/large geom); `full` = all 6 points. |
| `--only` / `--skip` / `--list` | Additional name-based selection; `--list` prints and exits. |
| `--extra-specs FILE` / `--replace` | Append (or replace) the built-in list from a JSON file of spec dicts. |
| `--rtl-only` | Shortcut for `--stop-after rtl`; fastest check the spec plumbing reaches `garnet.py`. |
| `--stop-after STEP` | Run `make` up to a **real mflowgen step name** (validated via `make list` in `_check_step_exists`, line 581, to catch construct-variable-vs-step-name typos). |
| `--fresh` | `rm -rf` each workspace before building — a total wipe, stronger than mflowgen's own clean (`42a174d8`). Overrides `--clean*` and `--skip-existing`. |
| `--clean STEPS` / `--clean-all` | Map to mflowgen's `make clean-<name>` / `clean-all` to force step (and downstream) rebuilds while keeping the Makefile (`62ad6a37`). |
| `--make TARGETS` | Passthrough: run `make <targets>` (`status`, `list`, `runtimes`, `clean-*`) in each existing workspace and exit, output to terminal (`09ef7a6c`). |
| `--parallel-jobs N` | `make -jN` **within** one build. |
| `--config-jobs M` | Build **M configs concurrently** via a `ThreadPoolExecutor` (`b32f5a7f`); independent workspaces. Effective load ≈ M×N — mind RAM and Genus/Innovus licenses (2×`-j6` is a noted sweet spot). |
| `--use-sim-sram` | Behavioral SRAM instead of a hardened macro (for geometries with no matching physical macro). |
| `--power` | Run the app-driven power leaves instead of stopping at signoff (see §e). |
| `--skip-existing` / `--dry-run` | Skip workspaces with a `done.flag`; print commands without running. |

**Preflight guard** (`_preflight`, line 301; `55f41a54`). Hard-errors on a
**stale in-tree `garnet/sweep_out`** because `gen_rtl` `docker cp`s the garnet
checkout into the build container, and an in-tree mflowgen workspace holds
absolute adk symlinks that `docker cp` rejects (`invalid symlink …`). It also
warns (not fatal) when `garnet.py` lacks `--lake-spec-config` (wrong branch),
and when `--out-dir` is itself inside the garnet checkout (`main`, line 247).

**How to run**

```bash
# List the selected config names, touch nothing
./mflowgen/sweep_specs.py --preset smoke4 --list

# One smoke point, RTL only (fast plumbing check)
./mflowgen/sweep_specs.py --rtl-only --only fw1_dw16_sc4096_sp_in1_out1

# Full sweep through signoff, 2 configs at a time, make -j6 each
./mflowgen/sweep_specs.py --preset full --config-jobs 2 --parallel-jobs 6 \
    --out-dir /sim/mstrange/sweep_out/tile_memcore_pnr
```

Results go to `<out-dir>/results.csv` (PASS/FAIL/SKIP, spec fields, workspace,
duration). **Keep `--out-dir` outside the garnet checkout** (symlink breakage
above).

---

## (b) RTL generation / containerized build — `mflowgen/common/rtl/gen_rtl.sh`

**What / why.** `gen_rtl.sh` emits `design.v` for a tile/graph. On `modern_gf`
it learned to (1) forward the lake-spec knobs to `aha garnet`, and (2) build
robustly from a **host garnet + lake copied into the aha docker container**.

**Lake-spec forwarding** (lines 86–109). Empty knobs are no-ops (preserves
behavior for `Tile_PE`/`glb_top`). When `lake_spec_config` is set it is resolved
to an absolute host path, verified to exist, `docker cp`-ed to
`/tmp/lake_spec_config.json` in the container (lines 204–207), and passed as
`--lake-spec-config` (+ optional `--lake-spec-mode`). The non-container path
(lines 396–401) points `garnet.py` at the host file directly and rewrites the
container path baked into `$flags`.

**Container hardening** (the `1d8a816c`/`b8929f02`/`684b25e5`/`28928b70`/`4c76d298`
sequence):
- `docker cp` the **host** `$GARNET_HOME` and `$LAKE_PATH` (defaults to a `lake`
  sibling of `$GARNET_HOME`) into `/aha/garnet` and `/aha/lake`, **keeping
  `.git`** (plain `docker cp`, not a tar stream) so the in-container
  `git fetch/checkout` works (lines 181–199).
- Because the copied-in repos keep **host ownership** (≠ container user), git
  refuses to operate on them ("dubious ownership"); the build adds scoped
  `git config --global --add safe.directory /aha/{garnet,lake}` (lines 285–286).
- **lake `THESIS` checkout** (lines 312–321): inside the container it runs
  `git fetch origin THESIS && git checkout -B THESIS origin/THESIS` on
  `/aha/lake`, in a **subshell** so a failing fetch cannot strand the CWD, and
  **fails loudly** if the checkout fails. This is how a pushed lake `THESIS` fix
  reaches the build **without** a manual lake pull on the build machine.
- **`⚠ Fragile-by-construction`:** the entire container body is a host
  double-quoted `docker exec "…"` string. `4c76d298` fixed a bug where a double
  quote inside an added comment **truncated the whole script**. The in-file
  comments explicitly warn: no `"`, `` ` ``, or `$` in added text inside that
  string.

Downstream, `design.v` is the concatenation of `garnet.v` + `genesis_verif/*` +
the systemRDL outputs for the global buffer/controller, copied back out with
`docker cp` (lines 340–362).

`garnet.py` gained `--lake-spec-config` / `--lake-spec-mode` (garnet.py lines
1063–1065) which re-export `LAKE_SPEC_CONFIG`/`LAKE_SPEC_MODE`; `cgra/util_onyx.py`
(lines 188–202) reads the JSON and derives `mem_width = data_width * vec_width`
and `mem_depth = storage_capacity // (mem_width//8)`, and sets
`true_dual_port` from `dual_port`. Only `vec_width`, `data_width`,
`storage_capacity` (plus `dual_port`) affect the RTL; other spec keys are
provenance only.

The same knobs are forwarded by the fabric/full-chip graphs too:
`mflowgen/tile_array/construct.py` (lines 55–59, 524–525) and
`mflowgen/full_chip/construct.py` (lines 89–93), so the sweep can also target
those graphs, not only `Tile_MemCore`.

---

## (c) Tile_MemCore floorplan + spec-aware SRAM macro

### Spec-aware SRAM macro — `mflowgen/common/gen_sram_macro_spec/`

**What / why.** The default `common/gen_sram_macro` builds a **fixed** 512×32
macro from `num_words/word_size/mux_size` parameters — which blackboxes for any
other geometry. A lake-spec build instantiates whatever SRAM geometry lake chose
per spec, so the hardened macro must **match the RTL**. New step
`gen_sram_macro_spec` (`1f28222f`, ported from `lake/pd/thesis/gen_sram_macro`)
does this:

- **`get_macro_name.py`** reads `inputs/design.v`, finds the macro the RTL
  instantiated (lake names the hardened SRAM child `mem_stub`), and extracts the
  exact GF12 master name via regex
  `IN12LP_(S1DB|S1PB|SDPB|R2PB)_W\d+B\d+M\d+S\d+_[HL]`. It matches the **module
  master** name (not the instance), so a uniquified instance like `..._H_0_0`
  still resolves. It derives the SRAM **family** token from the name.
- **`gen_srams.sh`** builds *exactly* that macro with the GF12 memory compiler
  (`IN12LP_MEM_genviews`), selecting the compiler binary by family
  (`v-comp_in_gf12lp_{s1db|s1pb|sdpb|r2pb}`), and symlinks the views into the
  garnet-expected output names (`sram_tt.lib`, `sram_ff.lib`, `sram.gds`,
  `sram.lef`, `sram_pwr.v`, `sram.v`, `sram.spi`), then builds `sram_tt.db` via
  `lib2db/`.

**Wiring** (`Tile_MemCore/construct.py` line 145): `spec_sram = bool(lake_spec_config)
and not use_sim_sram`. When true, the graph swaps `gen_sram_macro` →
`gen_sram_macro_spec` and adds an edge `rtl → gen_sram` (line 383) so the macro
step sees `design.v`. Behavioral (`use_sim_sram`) builds keep the fixed step
(its lib is unused).

### Floorplan die-sizing — `Tile_MemCore/custom-init/outputs/floorplan.tcl`

**What / why.** `core_height` is **fixed** (226 rows on gf12) so MemCore and PE
tiles abut in the array. But a low-mux spec SRAM (e.g. the fw8
`W02048B064M04` point) is physically **taller** than that fixed height — the
centered placement then lands the macro at **negative y** ("out of design Box",
IMPSP-606) and `routeDesign` fails on >100 % density / overlaps
(`b290c3c8`/`26affa0c`/`3e729f78`).

The fix (lines 55–105) measures the SRAM block **up front** and grows the die
**only when it overflows** the fixed height:
- height ← needed block height + margins + halo slack;
- width ← sized to hold **both** the fixed macros **and** the std cells at the
  density target (`total_cell_area/density + macro_area`, not std area alone —
  otherwise macros squeeze std placement into slivers and trip NRIG-76);
- both dims snapped up to the site grid.

Crucially this is **self-gated on the actual overflow** — it does *not* read a
spec env var (which is **not** exported to the init step). So a MemCore whose
macro already fits the fixed height (the default onyx build, and most spec
configs that prefer short `cols=2` macros) **never enters the grow branch and is
byte-identical**.

---

## (d) Mode-constraints correctness — `Tile_MemCore/constraints/constraints.tcl`

**What / why.** The three timing scenarios (`UNIFIED_BUFFER`, `FIFO`, `SRAM`)
apply `set_case_analysis` on `MemCore_inner_W/mode[0]` / `mode[1]`. The classic
onyx MemCore has a 2-bit `mode[1:0]` bus (several controllers). **Spec-generated
MemCores do not** — verified against real `garnet.py` RTL, where
`MemCore_inner_W` declares `input logic mode`, a **1-bit scalar** (the rest
carried by `mode_excl`). `set_case_analysis` on `mode[0]`/`mode[1]` then aborts
Genus synthesis with **TUI-61**.

`1f28222f` added a `_obj_exists` helper (line 50) that detects `mode[0]` once via
`get_pins`/`get_ports`; `has_mode` gates all six `set_case_analysis` calls, so
single-controller (spec) designs synthesize by analyzing the real logic without
pinning `mode`. `d92fa948` then **corrected the explanatory comment** (lines
40–49) to reflect the RTL-verified rationale — the code was already right; the
prior comment mis-described *why*.

---

## (e) Power flow — post-synth, post-pnr, and RTL-activity (ptpx-rtl)

The Tile_MemCore graph can emit **application-driven dynamic power** (a real
Halide app's switching activity → PrimeTime-PX). Three power leaves exist:

| Leaf | Netlist analyzed | Activity source |
|---|---|---|
| `tile-post-synth-power` | synthesized netlist | app SAIF (gate) |
| `tile-post-pnr-power` | routed signoff netlist | gate-level sim SAIF |
| `tile-post-rtl-power` | routed signoff netlist | **RTL-sim** SAIF, bound via the Genus name map |

**RTL-activity level** (`8b4e56da`, the HEAD commit) is the new addition.
`mflowgen/common/tile-post-rtl-power/` is a sub-graph that mirrors
`tile-post-pnr-power` but swaps the gate-level sim for an **RTL sim** of
`design.v` and swaps `ptpx-gl` for the new **`synopsys-ptpx-rtl`**. The trick:
power is still computed on the *signed-off gate netlist* (`design.vcs.v` + spef +
`pt.sdc`), but the RTL-name `run.saif` is bound onto the gate netlist by
`source`-ing the Genus **`design.namemap`** (RTL→gate name mapping written by
`custom-genus-scripts/generate-results.tcl` via `write_name_mapping`, and
surfaced as a synth output `synth.extend_outputs(["design.namemap"])`,
construct.py line 244). `synopsys-ptpx-rtl/configure.yml` consumes
`design.vcs.v`, `design.spef.gz`, `design.pt.sdc`, `run.saif`, `design.namemap`
and emits `power.hier`.

**Opt-in.** Two independent env switches read at graph-materialization time
(construct.py lines 32–41): `SYNTH_POWER` adds `post_synth_power`, `RTL_POWER`
adds `post_rtl_power`; **either disables power-aware PnR** (`pwr_aware = False`).
`sweep_specs.py --power` (`bc02d0d9`, extended in `8b4e56da`) sets **both** and
makes all three leaves — the `--power all-3` behavior — each of which pulls the
full PnR plus the `application` sim (default app `tests/conv_3_3`) as
dependencies. Needs docker + Cadence (Innovus/Xcelium) + PrimeTime, i.e. the
build machine.

The sub-graph can also be driven standalone via
`tile-post-rtl-power/run_all_tiles.py`, which iterates
`inputs/tiles_<design>.list` and runs `run.sh` per tile.

---

## (f) mflowgen helper scripts

Both live under `mflowgen/` and exist because the **build machine can't run
Claude** — they help a human drive/observe long PnR runs over ssh.

- **`watch_step.sh`** (`ed560bd2`). Live-follows the currently-running mflowgen
  step's log. A step is "running" when its `NN-stepname/` dir has a
  `.time_start` but no `.time_end`; the script streams that log and
  **auto-hops** to the next step when one finishes, maintaining a stable
  `current-step.log` symlink. Modes: `--symlink-only`, `--list`. No deps beyond
  bash + coreutils.
- **`logclip.sh`** (`83803d91`). Copies a build log to your **local** clipboard
  over ssh + tmux via **OSC 52** (no X11/xclip/pbcopy). Default = the active
  step's log; `--all` (concat every step), `--make` (top-level `make.log`),
  `--step <NN-name>`, `--lines N`, `--print`. Requires tmux
  `set-clipboard on` + `allow-passthrough on`.

---

## Relationship to lake

garnet **consumes** lake MEM-tile specs and collateral. The sweep exports a lake
spec (`storage_capacity`/`data_width`/`vec_width`/`dual_port`, …) as
`LAKE_SPEC_CONFIG`; `gen_rtl.sh` checks out **lake's `THESIS` branch inside the
container** and runs `aha garnet --lake-spec-config …`, so lake generates the
per-spec MemCore RTL **and** picks the SRAM macro geometry. garnet then hardens
*exactly that macro* (`gen_sram_macro_spec` reads the macro name back out of the
RTL) and pushes the tile through PnR + power. In short: **lake decides the memory;
garnet lays it out and measures it.** For the lake side (tech-map/column
selection, dual-port fixes, the thesis SRAM flow this was ported from), see the
companion [`LAKE.md`](LAKE.md) and `/aha/lake/CLAUDE.md` §5.

---

## Uncommitted / in-flight state

`git status` in `/aha/garnet` shows **no uncommitted *tracked* diffs** — the
`modern_gf` work is fully committed. The only working-tree entries are:

- **Generated build artifacts** (untracked, expected): `global_buffer/header/`,
  `global_buffer/systemRDL/{glb.rdl,output/}`, `global_controller/header/`,
  `global_controller/systemRDL/output/`, `global_controller/systemRDL/rdl_models/glc.rdl.final`,
  `matrix_unit/header/`. These are systemRDL/header outputs produced by a build,
  not source.
- **`mflowgen/CLAUDE.md`** (untracked): session notes for this work — the
  authoritative running log for the sweep. Distilled into this document.

If any of the tracked `modern_gf` content is unexpectedly missing on a machine,
prior work may have been lost — check before assuming baseline.

---

## Operational caveat — the standalone build machine

Per session memory (`project_build_machine_standalone_garnet`) and
`mflowgen/CLAUDE.md`: the sweep actually runs from a **standalone garnet
checkout at `/sim/mstrange/BUILD_CGRA/garnet`** (with a sibling `lake`), because
`/aha` has no docker/gf12-adk/Cadence. **aha gitlink bumps do NOT update that
checkout** — fixes must be applied there by a direct `git pull`. Lake fixes flow
separately via `origin/THESIS` (checked out in-container by `gen_rtl.sh`). Keep
`sweep_out` **out of** that checkout (the `docker cp` absolute-symlink breakage).
RTL generation alone *can* be validated locally on `/aha` (`garnet.py` runs;
~1 min/config) even though synth/PnR cannot — see
`reference_local_memcore_rtl_validation`.
