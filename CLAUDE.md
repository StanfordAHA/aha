# /aha — Root notes for Claude sessions

This is the top-level of the Halide-to-Hardware → Clockwork → CGRA accelerator toolchain. It's a monorepo whose subdirectories are separate git repos (some upstream, some forked). Most real work happens in one or two subrepos at a time.

## Read this first when a session starts

Before touching code, orient by reading — in this order:

1. **This file** — you're doing that now.
2. **The `CLAUDE.md` of any subrepo you're about to work in.** These hold notes from prior Claude sessions that survived beyond one conversation: file maps, build recipes, root causes of bugs, uncommitted-state checklists, "why-this-hack-exists" context.
3. **The tail of `/aha/SESSION_LOG.md`** (`tail -n 80`). It shows what other sessions did recently and what they're working on now. Several sessions often run at once on this machine, so check it before you edit shared files.

Do NOT read or edit child subrepo `README.md` files unless the user explicitly asks. Upstream READMEs are for humans and should be left alone.

## Subrepos and where session notes should live

Every subrepo may have a `CLAUDE.md` for session notes. Create one when you learn something worth carrying forward. Leave `README.md` alone.

Current state (as of this file's creation):

| Subrepo | Purpose | Has CLAUDE.md |
|---|---|---|
| `Halide-to-Hardware/` | Halide frontend + apps (`apps/hardware_benchmarks/`) that lower to clockwork | no |
| `clockwork/` | Polyhedral compiler that lowers Halide-emitted IR to controller configs and CoreIR | **yes** |
| `garnet/` | CGRA fabric generator (produces the tile RTL + lake collateral) | **`mflowgen/CLAUDE.md`** (lake-spec MemCore PnR sweep) |
| `lake/` | MEM tile generator (SRAM + agg + tb + controllers) — where fetch_width comes from | **yes** |
| `canal/` | Interconnect generator | no |
| `mflowgen/` | Backend physical-design flow (PnR, mflowgen graphs) | no |
| `coreir/` | HW IR + code generation library | no |
| `Lego_v0/` | Newer app framework | no |
| `MetaMapper/` | Post-map optimization | no |
| Others | Peripheral tools (magma, mantle, gemstone, kratos, hwtypes, ast_tools, peak, cosa, pono, sam, strait, voyager, rdai, etc.) | no |

When adding a subrepo `CLAUDE.md`, add its row here. Never create a `README.md` yourself.

## The main `aha` CLI driver

`aha` is a Python package under `/aha/aha/` that orchestrates the full flow. Key commands:

- `aha halide <app>` — runs Halide → clockwork → mapping. Flags to know:
  - `--log` — writes to `log/aha_map.log` inside the app dir.
  - `--stop-after-clockwork` — stops after `make compile_mem` (skips CGRA placement). Local addition; see `aha/util/map.py`.
- `aha sweep_conv_block_sizes` — sweep driver for conv_3_3 across schedule variants (local addition; see `aha/util/sweep_conv_block_sizes.py`).
- `aha sweep_tile_memcore_pnr` — mflowgen driver for per-spec MemCore RTL through PnR (local addition).
- `aha map/halide --pond-collateral <json>` — PE-tile pond's lake collateral for clockwork's `regfile` level (`LAKE_COLLATERAL_JSON_REGFILE`, next to `--collateral` for MEM); auto-generated from `LAKE_POND_SPEC_CONFIG` when set. Local addition (clockwork side: `clockwork/CLAUDE.md` "Pond (regfile level)").

## Uncommitted state to be aware of

Several subrepos carry uncommitted changes across sessions. Before assuming baseline behavior, run `git status` in the subrepo you're about to touch. Known live changes (as of session cluster around 2026-05):

- `clockwork/`: `isl_utils.{cpp,h}`, `ubuffer.cpp`, `coreir_backend.cpp` — split-mem fixes. See `clockwork/CLAUDE.md` for details.
- `Halide-to-Hardware/`: `apps/hardware_benchmarks/tests/conv_3_3/{conv_3_3_generator.cpp,process.cpp,Makefile}` — conv_3_3 parameterized for the sweep.
- `/aha/aha/`: `util/map.py`, `util/sweep_conv_block_sizes.py`, `util/sweep_tile_memcore_pnr.py` — sweep drivers + `--stop-after-clockwork` flag.

If any subrepo's `git status` is unexpectedly clean, prior session's work has been lost — check with the user before assuming baseline.

## Where the sweep output lives

`/aha/sweep_out/` holds per-config artifacts (`design_top.json`, `conv_3_3_garnet.json`, `cgra_resource_estimation.csv`, `mem_cout`, and `sweep_results.csv`) from sweep runs. Do not commit — it's ephemeral experiment output.

## Memory system

Claude's cross-session memory lives at `/root/.claude/projects/-aha/memory/`. Read `MEMORY.md` there for what's tracked. Repo-specific notes go in the subrepo's CLAUDE.md; user-preference and project-wide notes go in memory. Don't duplicate.

## Session log (REQUIRED for every session)

`/aha/SESSION_LOG.md` is the shared, append-only record of what each Claude session did. It is the one place both the user and other sessions can see all recent work. (User rule, 2026-10-01.)

- **When to write:** add an entry when you start non-trivial work that touches shared files (mark it `in progress` and list the files you're editing). Add another entry when you finish, hand off, or stop with work partly done. Also add one after any commit or push. Read-only Q&A sessions don't need an entry.
- **How to write:** only APPEND with a shell heredoc (`cat >> /aha/SESSION_LOG.md <<'EOF' … EOF`). Never use Write or Edit on this file, and never rewrite or reorder past entries. Concurrent sessions append to it, so a read-modify-write can wipe out someone else's entry. To correct an old entry, append a new one that says what changed.
- **Entry format** (keep each one short, ~5–15 lines):
  ```
  ## <YYYY-MM-DD HH:MM> · <session id, first 8 chars> · <topic> · <in progress|done|handed off|blocked>
  - Repos/files: <subrepo: files touched>
  - Did: <what changed + what it was verified against>
  - Commits/pushes: <repo@sha, branch, pushed?> (or "none")
  - Uncommitted: <what's left dirty and where>
  - Details: <pointer to the subrepo CLAUDE.md section / memory file / scratchpad that holds the real notes>
  ```
  Your session id is the UUID in your scratchpad path (`/tmp/claude-0/-aha/<uuid>/scratchpad`).
- **What goes where:** the log records *what happened and when* and points elsewhere. Root causes, recipes and file maps still go in the subrepo `CLAUDE.md` or in memory. Don't copy them into the log.
- The file is local-only. It is listed in `.git/info/exclude`, so don't commit it.
