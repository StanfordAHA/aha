"""Sweep thesis experiment specs through clockwork compilation of conv_3_3.

Generates collateral JSON files for all unique hardware configurations from
lake's all_experiments_thesis.sh, then runs clockwork compilation against
each to determine which configs can successfully compile conv_3_3.

Usage:
    python -m aha.util.sweep_thesis_collateral [--generate-only] [--compile-only]
"""

import argparse
import csv
import glob as globmod
import itertools
import json
import math
import os
import shlex
import shutil
import subprocess
import sys

from lake.spec.spec import Spec
from lake.spec.port import Port
from lake.spec.storage import SingleBankStorage
from lake.spec.memory_port import MemoryPort
from lake.spec.iteration_domain import IterationDomain
from lake.spec.address_generator import AddressGenerator
from lake.spec.schedule_generator import ScheduleGenerator, ReadyValidScheduleGenerator
from lake.utils.spec_enum import Runtime, Direction, MemoryPortType


# build_spec / build_spec_rv now live in lake, so that garnet's
# cgra/util_onyx.py can import them inside the rtl docker container
# (which ships lake but not this package). Re-exported here to keep
# existing callers working and to avoid a second copy drifting.
from lake.spec.spec_memory_controller import build_spec, build_spec_rv  # noqa: F401




def enumerate_thesis_configs():
    """Enumerate all unique configurations from all_experiments_thesis.sh.

    Returns a list of dicts, each with the parameters for build_spec().
    Deduplicates configs that produce identical collateral.
    """
    configs = []

    # PORT_EXP group 1: fw=4, dw={8,16,32}, sc=8192, in=2, out=2
    for dw in [8, 16, 32]:
        configs.append(dict(storage_capacity=8192, data_width=dw, vec_width=4,
                            in_ports=2, out_ports=2))

    # PORT_EXP group 2: fw={2,4,8}, vc={2,4,8}, dw={8,16}, sc=8192
    for fw, vc, dw in itertools.product([2, 4, 8], [2, 4, 8], [8, 16]):
        configs.append(dict(storage_capacity=8192, data_width=dw, vec_width=fw,
                            vec_capacity=vc, in_ports=2, out_ports=2))

    # PORT_EXP group 3: fw={2,4}, vc={2,4,8}, dw=32, sc=8192
    for fw, vc in itertools.product([2, 4], [2, 4, 8]):
        configs.append(dict(storage_capacity=8192, data_width=32, vec_width=fw,
                            vec_capacity=vc, in_ports=2, out_ports=2))

    # PORT_EXP group 4: fw=2, vc={2,4,8}, dw=64, sc=8192
    for vc in [2, 4, 8]:
        configs.append(dict(storage_capacity=8192, data_width=64, vec_width=2,
                            vec_capacity=vc, in_ports=2, out_ports=2))

    # ITERATION_DOMAIN_EXP: fw=1, dw=16, sc=8192, dims={1..6}, max_extent={64,256,1024,4096}
    for dims_, me in itertools.product([1, 2, 3, 4, 5, 6], [64, 256, 1024, 4096]):
        configs.append(dict(storage_capacity=8192, data_width=16, vec_width=1,
                            dims=dims_, max_extent=me, in_ports=2, out_ports=2))

    # AFFINE_PATTERN_GEN_EXP: fw=1, dw=16, sc=8192, dims={1..6}, max_sequence_width varies
    # max_sequence_width only affects stride_width which is NOT in collateral, so
    # these collapse to dims={1..6} with default counter_ub=2047
    for dims_ in [1, 2, 3, 4, 5, 6]:
        configs.append(dict(storage_capacity=8192, data_width=16, vec_width=1,
                            dims=dims_, in_ports=2, out_ports=2))

    # MEMORY_EXP: dual port configs
    # fw=1, dp, in=1, out=1, dw=16
    for sc in [1024, 2048, 4096, 8192, 16384]:
        configs.append(dict(storage_capacity=sc, data_width=16, vec_width=1,
                            dual_port=True, in_ports=1, out_ports=1))
    # fw=2, dp, in=2, out=2, dw=16
    for sc in [1024, 2048, 4096, 8192, 16384]:
        configs.append(dict(storage_capacity=sc, data_width=16, vec_width=2,
                            dual_port=True, in_ports=2, out_ports=2))
    # fw=4, dp, in=4, out=4, dw=16
    for sc in [1024, 2048, 4096, 8192]:
        configs.append(dict(storage_capacity=sc, data_width=16, vec_width=4,
                            dual_port=True, in_ports=4, out_ports=4))

    # MEMORY_EXP: single port configs
    # fw=2, sp, in=1, out=1, dw=16
    for sc in [2048, 4096, 8192, 16384, 32768]:
        configs.append(dict(storage_capacity=sc, data_width=16, vec_width=2,
                            in_ports=1, out_ports=1))
    # fw=4, sp, in=2, out=2, dw=16
    for sc in [4096, 8192, 16384, 32768]:
        configs.append(dict(storage_capacity=sc, data_width=16, vec_width=4,
                            in_ports=2, out_ports=2))
    # fw=8, sp, in=4, out=4, dw=16
    for sc in [8192, 16384, 32768]:
        configs.append(dict(storage_capacity=sc, data_width=16, vec_width=8,
                            in_ports=4, out_ports=4))

    return deduplicate_configs(configs)


def supports_pretest_end_to_end(cfg):
    return cfg.get("data_width", 16) == 16


def supports_aha_sweep_port_shape(cfg):
    # Keep the AHA sweep to configurations whose external port count is
    # commensurate with the fetch width. The raw thesis collateral source list
    # includes some legacy harness-shaped configs (for example inherited 2-in /
    # 2-out scalar cases), but for the AHA testing path we only keep shapes that
    # make sense for the memory tile itself:
    #   * single-port memory: in_ports + out_ports <= fetch_width
    #   * dual-port memory:   in_ports + out_ports <= 2 * fetch_width
    fw = cfg.get("vec_width", 1)
    total_ports = cfg.get("in_ports", 2) + cfg.get("out_ports", 2)
    max_total_ports = 2 * fw if cfg.get("dual_port", False) else fw
    return total_ports <= max_total_ports


def unsupported_aha_sweep_reason(cfg):
    total_ports = cfg.get("in_ports", 2) + cfg.get("out_ports", 2)
    fw = cfg.get("vec_width", 1)
    if cfg.get("dual_port", False):
        max_total_ports = 2 * fw
        if total_ports > max_total_ports:
            return (
                f"dual-port config has in+out={total_ports}, which exceeds "
                f"2*fetch_width={max_total_ports}"
            )
    else:
        max_total_ports = fw
        if total_ports > max_total_ports:
            return (
                f"single-port config has in+out={total_ports}, which exceeds "
                f"fetch_width={max_total_ports}"
            )
    return None


def unsupported_runtime_reason(cfg, mode):
    if mode == "rv" and cfg.get("vec_width", 1) > 1 and cfg.get("vec_capacity", 2) > 2:
        return (
            "RV wide-fetch currently supports vec_capacity <= 2 only; "
            "skipping larger SIPO/PISO cases"
        )
    return None


def config_key(cfg):
    """Return a hashable key representing the collateral-relevant parameters."""
    return (
        cfg.get('storage_capacity', 4096),
        cfg.get('data_width', 16),
        cfg.get('vec_width', 4),
        cfg.get('dims', 6),
        cfg.get('in_ports', 2),
        cfg.get('out_ports', 2),
        cfg.get('dual_port', False),
        cfg.get('vec_capacity', 2),
        cfg.get('max_extent'),
    )


def config_name(cfg):
    """Generate a short descriptive name for a configuration."""
    fw = cfg.get('vec_width', 4)
    dw = cfg.get('data_width', 16)
    sc = cfg.get('storage_capacity', 4096)
    dp = cfg.get('dual_port', False)
    inp = cfg.get('in_ports', 2)
    outp = cfg.get('out_ports', 2)
    vc = cfg.get('vec_capacity', 2)
    dims = cfg.get('dims', 6)
    me = cfg.get('max_extent')

    parts = [f"fw{fw}_dw{dw}_sc{sc}"]
    if dp:
        parts.append("dp")
    else:
        parts.append("sp")
    parts.append(f"in{inp}_out{outp}")
    if fw > 1:
        parts.append(f"vc{vc}")
    if dims != 6:
        parts.append(f"dim{dims}")
    if me is not None:
        parts.append(f"me{me}")
    return "_".join(parts)


def deduplicate_configs(configs):
    """Remove duplicate configurations."""
    seen = set()
    unique = []
    for cfg in configs:
        k = config_key(cfg)
        if k not in seen:
            seen.add(k)
            unique.append(cfg)
    return unique


def generate_all_collateral(output_dir, configs):
    """Generate collateral JSON files for all configs.

    Each config gets its own subdirectory under output_dir so that the
    collateral sits alongside compilation outputs collected later.

    Returns list of (config, name, collateral_path, collateral_dict) tuples.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []

    for cfg in configs:
        name = config_name(cfg)
        cfg_dir = os.path.join(output_dir, name)
        os.makedirs(cfg_dir, exist_ok=True)
        path = os.path.join(cfg_dir, "lake_collateral.json")

        spec = build_spec(**cfg)
        collateral = spec.extract_compiler_information()
        spec.save_compiler_information(path)

        results.append((cfg, name, path, collateral))

    return results


def print_collateral_summary(generated):
    """Print a summary table of all generated collateral files."""
    # Header
    print(f"\n{'Config':<55} {'sram':>5} {'agg':>4} {'tb':>4} {'fw':>3} "
          f"{'in':>3} {'out':>3} {'iter':>4} {'cub':>5} {'dp':>5}")
    print("-" * 100)

    for cfg, name, path, coll in generated:
        sram = coll['capacity'].get('sram', '-')
        agg = coll['capacity'].get('agg', '-')
        tb = coll['capacity'].get('tb', '-')
        fw = coll['fetch_width']
        inp = coll['interconnect_in_num']
        outp = coll['interconnect_out_num']
        il = coll['iteration_level']
        cub = coll['counter_ub']
        dp = coll['dual_port_sram']

        print(f"{name:<55} {str(sram):>5} {str(agg):>4} {str(tb):>4} {fw:>3} "
              f"{inp:>3} {outp:>3} {il:>4} {cub:>5} {str(dp):>5}")

    print(f"\nTotal: {len(generated)} unique configurations")


def run_clockwork_compilation(collateral_path, app_dir, clockwork_path):
    """Run clockwork_codegen with the given collateral file.

    The binary returns non-zero even on scheduling success because the
    post-scheduling regression testbench compilation may fail (missing
    headers when run outside ``make map``). We determine success by
    checking whether map_result/<testname>/<testname>.json was produced.

    Returns (success: bool, error_msg: str or None).
    """
    codegen_bin = os.path.join(app_dir, "bin", "clockwork_codegen")
    if not os.path.exists(codegen_bin):
        return False, "clockwork_codegen binary not found"

    # Determine testname from the app directory
    testname = os.path.basename(app_dir)
    map_result_json = os.path.join(app_dir, "bin", "map_result",
                                   testname, f"{testname}.json")
    # Remove old result so we can detect fresh output
    if os.path.exists(map_result_json):
        os.remove(map_result_json)

    env = os.environ.copy()
    env["LAKE_COLLATERAL_JSON_MEM"] = collateral_path
    env["CLKWRK_PATH"] = clockwork_path
    env["LD_LIBRARY_PATH"] = f"{clockwork_path}/lib:{env.get('LD_LIBRARY_PATH', '')}"
    lake_path = os.environ.get("LAKE_PATH", "/aha/lake")
    env["LAKE_PATH"] = lake_path
    env["LAKE_CONTROLLERS"] = os.path.join(app_dir, "bin")
    env["LAKE_STREAM"] = os.path.join(app_dir, "bin")
    coreir_path = os.environ.get("COREIR_PATH", "/aha/coreir")
    env["COREIR_PATH"] = coreir_path

    try:
        result = subprocess.run(
            [codegen_bin, "compile_mem_use_metamapper"],
            cwd=os.path.join(app_dir, "bin"),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        # Check for map_result output (scheduling success) regardless of
        # exit code — the regression testbench step may fail on missing
        # headers but the scheduling itself succeeded.
        if os.path.exists(map_result_json):
            return True, None

        # No map result produced — real scheduling failure
        err_lines = result.stderr.strip().split('\n')
        err_summary = '\n'.join(err_lines[-3:]) if len(err_lines) > 3 else result.stderr.strip()
        return False, err_summary
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (>300s)"
    except Exception as e:
        return False, str(e)


def collect_outputs(config_name, app_dir, output_dir):
    """Copy compilation outputs into a per-config directory alongside collateral.

    Creates ``<output_dir>/<config_name>/`` containing:
      - The collateral JSON (already there from generation)
      - map_result/  (final + intermediate memory mapping JSON)
      - Verilog (.v/.sv) generated in bin/
      - Key intermediate JSONs (design_top, mem_header, etc.)
    """
    testname = os.path.basename(app_dir)
    bin_dir = os.path.join(app_dir, "bin")
    dest = os.path.join(output_dir, config_name)
    os.makedirs(dest, exist_ok=True)

    # Copy map_result directory (final & intermediate mapping JSONs)
    map_result_src = os.path.join(bin_dir, "map_result")
    map_result_dst = os.path.join(dest, "map_result")
    if os.path.isdir(map_result_src):
        if os.path.exists(map_result_dst):
            shutil.rmtree(map_result_dst)
        shutil.copytree(map_result_src, map_result_dst)

    # Copy verilog files
    for pattern in ("*.v", "*.sv"):
        for f in globmod.glob(os.path.join(bin_dir, pattern)):
            shutil.copy2(f, dest)

    # Copy key intermediate JSON files produced by clockwork
    intermediate_jsons = [
        "design_top.json",
        "mem_header.json",
        f"{testname}_compute.json",
        f"{testname}_compute_kernel_latencies.json",
    ]
    for fname in intermediate_jsons:
        src = os.path.join(bin_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dest)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fout:
        json.dump(payload, fout, indent=2, sort_keys=True)


def summarize_log_tail(log_path, max_lines=20, max_chars=500):
    if not os.path.exists(log_path):
        return "log not found"
    with open(log_path) as fin:
        lines = [line.strip() for line in fin.readlines() if line.strip()]
    if not lines:
        return "empty log"
    summary = " | ".join(lines[-max_lines:])
    return summary[-max_chars:]


def run_logged_command(cmd, cwd, env, log_path, timeout=7200):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    bash_cmd = (
        "set -o pipefail && "
        f"{shlex.join(cmd)} 2>&1 | tee {shlex.quote(log_path)}"
    )
    try:
        result = subprocess.run(
            ["bash", "-lc", bash_cmd],
            cwd=cwd,
            env=env,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT (>{timeout}s)"

    if result.returncode == 0:
        return True, None
    return False, summarize_log_tail(log_path)


def copy_if_exists(src, dst_dir):
    if os.path.exists(src):
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(dst_dir, os.path.basename(src)))


def copytree_if_exists(src, dst):
    if os.path.isdir(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def collect_map_outputs_to_dir(app_dir, dest_dir):
    testname = os.path.basename(app_dir)
    bin_dir = os.path.join(app_dir, "bin")
    os.makedirs(dest_dir, exist_ok=True)
    copytree_if_exists(os.path.join(bin_dir, "map_result"),
                       os.path.join(dest_dir, "map_result"))
    for fname in (
        "design_top.json",
        "mem_header.json",
        f"{testname}_compute.json",
        f"{testname}_compute_kernel_latencies.json",
        "design_meta_halide.json",
        "design_meta.json",
    ):
        copy_if_exists(os.path.join(bin_dir, fname), dest_dir)


def collect_pnr_outputs_to_dir(app_dir, dest_dir):
    testname = os.path.basename(app_dir)
    bin_dir = os.path.join(app_dir, "bin")
    os.makedirs(dest_dir, exist_ok=True)
    for fname in (
        "design.place",
        "design.route",
        "design.packed",
        "design_post_pipe.packed",
        "design_post_pipe_compressed.packed",
        f"{testname}.bs",
        f"{testname}.bs.json",
        "design.port_remap",
        "netlist_info.txt",
        "design_top.json",
        "design_meta.json",
        "design_meta_halide.json",
        "cgra_config.json",
    ):
        copy_if_exists(os.path.join(bin_dir, fname), dest_dir)


def collect_garnet_outputs_to_dir(aha_dir, dest_dir):
    garnet_dir = os.path.join(aha_dir, "garnet")
    os.makedirs(dest_dir, exist_ok=True)
    for fname in ("garnet.v", "garnet_PE.v", "garnet_PE.json"):
        copy_if_exists(os.path.join(garnet_dir, fname), dest_dir)


def parse_runtime_modes(runtime_modes_arg):
    modes = [mode.strip() for mode in runtime_modes_arg.split(",") if mode.strip()]
    if not modes:
        raise ValueError("No runtime modes specified")
    invalid = [mode for mode in modes if mode not in ("rv", "static")]
    if invalid:
        raise ValueError(f"Invalid runtime modes: {invalid}")
    return modes


def filter_generated_configs(generated, config_name=None):
    if not config_name:
        return generated
    return [entry for entry in generated if entry[1] == config_name]


def build_runtime_env(base_env, mode, spec_config_path, collateral_path=None):
    env = base_env.copy()
    env["LAKE_SPEC_CONFIG"] = spec_config_path
    env["LAKE_SPEC_MODE"] = mode
    env["DENSE_READY_VALID"] = "1"
    env["USE_NON_SPLIT_FIFOS"] = "1"
    if collateral_path:
        env["LAKE_COLLATERAL_JSON_MEM"] = collateral_path
    else:
        env.pop("LAKE_COLLATERAL_JSON_MEM", None)
    if mode == "rv":
        env["EXHAUSTIVE_PIPE"] = "1"
    else:
        env.pop("EXHAUSTIVE_PIPE", None)
    return env


def load_prior_results(csv_path):
    """Load a prior results CSV.

    Returns (prior_rows, passed_pairs) where prior_rows is the full list of
    rows previously written (so we can seed the new run's results and preserve
    them in the rewritten CSV) and passed_pairs is a set of
    (config_name, runtime_mode) tuples with overall == 'PASS'.
    """
    if not os.path.exists(csv_path):
        return [], set()
    prior_rows = []
    passed_pairs = set()
    with open(csv_path, newline="") as fin:
        reader = csv.DictReader(fin)
        for row in reader:
            prior_rows.append(row)
            if row.get("overall") == "PASS":
                passed_pairs.add((row["config_name"], row["runtime_mode"]))
    return prior_rows, passed_pairs


def save_pretest_results(results, csv_path):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    fieldnames = [
        "config_name",
        "runtime_mode",
        "garnet_build",
        "map",
        "pnr",
        "overall",
        "artifact_dir",
        "notes",
    ]
    with open(csv_path, "w", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)


def print_pretest_results_table(results):
    print(f"\n{'Config':<55} {'mode':<6} {'garnet':<8} {'map':<6} {'pnr':<6} {'overall':<7}")
    print("=" * 100)
    for row in results:
        print(f"{row['config_name']:<55} {row['runtime_mode']:<6} "
              f"{row['garnet_build']:<8} {row['map']:<6} {row['pnr']:<6} {row['overall']:<7}")

    pass_count = sum(row["overall"] == "PASS" for row in results)
    skip_count = sum(row["overall"] == "SKIP" for row in results)
    fail_count = len(results) - pass_count - skip_count
    print(f"\nSummary: {pass_count} passed, {fail_count} failed, {skip_count} skipped, {len(results)} total")

    failed = [row for row in results if row["overall"] == "FAIL"]
    if failed:
        print("\nFailures:")
        for row in failed:
            print(f"  {row['config_name']} ({row['runtime_mode']}): {row['notes']}")

    skipped = [row for row in results if row["overall"] == "SKIP"]
    if skipped:
        print("\nSkipped:")
        for row in skipped:
            print(f"  {row['config_name']} ({row['runtime_mode']}): {row['notes']}")


def run_aha_map(collateral_path, aha_dir, app_name, log_path):
    env = os.environ.copy()
    cmd = [sys.executable, "-m", "aha.aha", "map", app_name, "--collateral", collateral_path]
    return run_logged_command(cmd, cwd=aha_dir, env=env, log_path=log_path, timeout=7200)


def run_garnet_build(aha_dir, spec_config_path, mode, width, height, glb_tile_mem_size, log_path,
                     dual_port=False):
    env = build_runtime_env(os.environ.copy(), mode, spec_config_path)
    cmd = [
        sys.executable, "garnet.py",
        "--width", str(width),
        "--height", str(height),
        "--verilog",
        "--use_sim_sram",
        "--glb_tile_mem_size", str(glb_tile_mem_size),
        "--lake-spec-config", spec_config_path,
        "--lake-spec-mode", mode,
        "--use-non-split-fifos",
    ]
    if dual_port:
        cmd.append("--dual-port")
    garnet_dir = os.path.join(aha_dir, "garnet")
    ok, err = run_logged_command(cmd, cwd=garnet_dir, env=env, log_path=log_path, timeout=7200)
    if not ok:
        garnet_v = os.path.join(garnet_dir, "garnet.v")
        log_has_done = False
        if os.path.exists(log_path):
            with open(log_path) as f:
                log_has_done = "garnet.py DONE" in f.read()
        if log_has_done and os.path.exists(garnet_v) and os.path.getsize(garnet_v) > 0:
            print(f"  garnet.py completed but crashed during shutdown — treating as success", flush=True)
            return True, None
    return ok, err


def run_aha_pnr(aha_dir, app_name, spec_config_path, collateral_path, mode,
                width, height, glb_tile_mem_size, log_path, dual_port=False):
    env = build_runtime_env(os.environ.copy(), mode, spec_config_path, collateral_path)
    cmd = [
        sys.executable, "-m", "aha.aha", "pnr", app_name,
        "--width", str(width),
        "--height", str(height),
        "--use_sim_sram",
        "--glb_tile_mem_size", str(glb_tile_mem_size),
        "--lake-spec-config", spec_config_path,
        "--lake-spec-mode", mode,
        "--use-non-split-fifos",
    ]
    if dual_port:
        cmd.append("--dual-port")
    return run_logged_command(cmd, cwd=aha_dir, env=env, log_path=log_path, timeout=7200)


def run_pretest_sweep(generated, aha_dir, app_name, app_dir, output_dir,
                      runtime_modes, width, height, glb_tile_mem_size, results_csv,
                      prior_rows=None, passed_pairs=None):
    results = list(prior_rows or [])
    passed_pairs = passed_pairs or set()
    total = len(generated)

    for index, (cfg, name, coll_path, _coll) in enumerate(generated, start=1):
        cfg_dir = os.path.join(output_dir, name)
        os.makedirs(cfg_dir, exist_ok=True)

        modes_to_run = [m for m in runtime_modes if (name, m) not in passed_pairs]
        if not modes_to_run:
            print(f"\n[{index}/{total}] {name} RESUME: all modes already PASS, skipping", flush=True)
            continue

        print(f"\n[{index}/{total}] Starting config {name}", flush=True)
        print(f"[{index}/{total}] collateral={coll_path}", flush=True)
        if len(modes_to_run) != len(runtime_modes):
            skipped = [m for m in runtime_modes if m not in modes_to_run]
            print(f"[{index}/{total}] RESUME: modes {skipped} already PASS, running {modes_to_run}", flush=True)

        map_log = os.path.join(cfg_dir, "aha_map.log")
        print(f"[{index}/{total}] map start -> {map_log}", flush=True)
        map_ok, map_err = run_aha_map(coll_path, aha_dir, app_name, map_log)
        print(f"[{index}/{total}] map {'PASS' if map_ok else 'FAIL'}", flush=True)
        if map_ok:
            collect_map_outputs_to_dir(app_dir, os.path.join(cfg_dir, "map"))

        for mode in modes_to_run:
            runtime_dir = os.path.join(cfg_dir, mode)
            os.makedirs(runtime_dir, exist_ok=True)
            spec_config_path = os.path.join(runtime_dir, "spec_config.json")
            write_json(spec_config_path, cfg)

            runtime_skip_reason = unsupported_runtime_reason(cfg, mode)
            if runtime_skip_reason:
                print(f"[{index}/{total}] {name} [{mode}] SKIP: {runtime_skip_reason}", flush=True)
                row = {
                    "config_name": name,
                    "runtime_mode": mode,
                    "garnet_build": "SKIP",
                    "map": "PASS" if map_ok else "FAIL",
                    "pnr": "SKIP",
                    "overall": "SKIP" if map_ok else "FAIL",
                    "artifact_dir": runtime_dir,
                    "notes": map_err or runtime_skip_reason,
                }
                results.append(row)
                save_pretest_results(results, results_csv)
                continue

            garnet_log = os.path.join(runtime_dir, "garnet_build.log")
            print(f"[{index}/{total}] {name} [{mode}] garnet start -> {garnet_log}", flush=True)
            garnet_ok, garnet_err = run_garnet_build(
                aha_dir, spec_config_path, mode, width, height,
                glb_tile_mem_size, garnet_log,
                dual_port=cfg.get('dual_port', False),
            )
            print(f"[{index}/{total}] {name} [{mode}] garnet {'PASS' if garnet_ok else 'FAIL'}", flush=True)
            if garnet_ok:
                collect_garnet_outputs_to_dir(aha_dir, runtime_dir)

            pnr_ok = False
            pnr_err = "skipped"
            pnr_log = os.path.join(runtime_dir, "aha_pnr.log")
            if map_ok and garnet_ok:
                print(f"[{index}/{total}] {name} [{mode}] pnr start -> {pnr_log}", flush=True)
                pnr_ok, pnr_err = run_aha_pnr(
                    aha_dir, app_name, spec_config_path, coll_path, mode,
                    width, height, glb_tile_mem_size, pnr_log,
                    dual_port=cfg.get('dual_port', False),
                )
                print(f"[{index}/{total}] {name} [{mode}] pnr {'PASS' if pnr_ok else 'FAIL'}", flush=True)
                if pnr_ok:
                    collect_pnr_outputs_to_dir(app_dir, os.path.join(runtime_dir, "pnr"))
            else:
                print(f"[{index}/{total}] {name} [{mode}] pnr SKIP", flush=True)

            notes = map_err or garnet_err or pnr_err or ""
            row = {
                "config_name": name,
                "runtime_mode": mode,
                "garnet_build": "PASS" if garnet_ok else "FAIL",
                "map": "PASS" if map_ok else "FAIL",
                "pnr": "PASS" if pnr_ok else ("SKIP" if not (map_ok and garnet_ok) else "FAIL"),
                "overall": "PASS" if (map_ok and garnet_ok and pnr_ok) else "FAIL",
                "artifact_dir": runtime_dir,
                "notes": notes,
            }
            results.append(row)
            save_pretest_results(results, results_csv)
            print(f"[{index}/{total}] {name} [{mode}] overall={row['overall']}", flush=True)

    return results


def run_sweep(generated, app_dir, clockwork_path, output_dir):
    """Run clockwork compilation for each config and collect results.

    Returns list of (name, collateral, success, error) tuples.
    """
    results = []
    total = len(generated)

    for i, (cfg, name, coll_path, coll) in enumerate(generated):
        print(f"[{i+1}/{total}] Compiling with {name}...", end=" ", flush=True)
        success, err = run_clockwork_compilation(coll_path, app_dir, clockwork_path)
        status = "PASS" if success else "FAIL"
        print(status)

        if success:
            collect_outputs(name, app_dir, output_dir)

        results.append((name, coll, success, err))

    return results


def print_results_table(results):
    """Print the final compilation results table."""
    print(f"\n{'Config':<55} {'sram':>5} {'agg':>4} {'fw':>3} "
          f"{'in':>3} {'out':>3} {'iter':>4} {'cub':>5} {'dp':>5} {'status':>6}")
    print("=" * 105)

    pass_count = 0
    fail_count = 0

    for name, coll, success, err in results:
        sram = coll['capacity'].get('sram', '-')
        agg = coll['capacity'].get('agg', '-')
        fw = coll['fetch_width']
        inp = coll['interconnect_in_num']
        outp = coll['interconnect_out_num']
        il = coll['iteration_level']
        cub = coll['counter_ub']
        dp = coll['dual_port_sram']
        status = "PASS" if success else "FAIL"

        if success:
            pass_count += 1
        else:
            fail_count += 1

        print(f"{name:<55} {str(sram):>5} {str(agg):>4} {fw:>3} "
              f"{inp:>3} {outp:>3} {il:>4} {cub:>5} {str(dp):>5} {status:>6}")

    print(f"\nSummary: {pass_count} passed, {fail_count} failed, {len(results)} total")

    if fail_count > 0:
        print("\nFailed configs:")
        for name, coll, success, err in results:
            if not success:
                print(f"  {name}: {err[:120] if err else 'unknown error'}")


def main():
    parser = argparse.ArgumentParser(
        description="Sweep thesis specs through clockwork compilation")
    parser.add_argument("--pretest", action="store_true",
                        help="Run the pre-test sweep: garnet build + aha map + aha pnr")
    parser.add_argument("--generate-only", action="store_true",
                        help="Only generate collateral, don't compile")
    parser.add_argument("--compile-only", action="store_true",
                        help="Only compile (assumes collateral already generated)")
    parser.add_argument("--config-name", type=str, default="",
                        help="Only run the named config (see config_name format)")
    parser.add_argument("--runtime-modes", type=str, default="rv,static",
                        help="Comma-separated runtime modes to run for --pretest (rv,static)")
    parser.add_argument("--width", type=int, default=4,
                        help="CGRA width for pre-test garnet/pnr runs")
    parser.add_argument("--height", type=int, default=8,
                        help="CGRA height for pre-test garnet/pnr runs")
    parser.add_argument("--glb-tile-mem-size", type=int, default=128,
                        help="GLB tile memory size for pre-test garnet/pnr runs")
    parser.add_argument("--results-csv", type=str, default="",
                        help="Path to incremental results CSV for --pretest")
    parser.add_argument("--resume", action="store_true",
                        help="For --pretest: skip (config, mode) pairs already marked PASS in results CSV")
    parser.add_argument("--aha-dir", type=str, default="/aha",
                        help="Path to the AHA repo root for --pretest commands")
    parser.add_argument("--app-name", type=str, default="tests/conv_3_3",
                        help="AHA app identifier for map/pnr commands in --pretest mode")
    parser.add_argument("--output-dir", type=str,
                        default="/tmp/thesis_collateral",
                        help="Directory for generated collateral files")
    parser.add_argument("--app-dir", type=str,
                        default="/aha/Halide-to-Hardware/apps/hardware_benchmarks/tests/conv_3_3",
                        help="Path to the app directory with clockwork_codegen")
    parser.add_argument("--clockwork-path", type=str,
                        default="/aha/clockwork",
                        help="Path to clockwork directory")
    args = parser.parse_args()

    all_configs = enumerate_thesis_configs()
    configs = [cfg for cfg in all_configs if supports_aha_sweep_port_shape(cfg)]
    if args.config_name:
        named_configs = [cfg for cfg in all_configs if config_name(cfg) == args.config_name]
        if not named_configs:
            raise ValueError(f"Config not found: {args.config_name}")
        configs = [cfg for cfg in named_configs if supports_aha_sweep_port_shape(cfg)]
        if not configs:
            raise ValueError(
                f"Config {args.config_name} is excluded from the AHA sweep: "
                f"{unsupported_aha_sweep_reason(named_configs[0])}"
            )

    skipped_configs = [cfg for cfg in all_configs if not supports_aha_sweep_port_shape(cfg)]
    if args.pretest:
        skipped_configs.extend(cfg for cfg in configs if not supports_pretest_end_to_end(cfg))
        configs = [cfg for cfg in configs if supports_pretest_end_to_end(cfg)]
        if args.config_name and not configs:
            raise ValueError(
                f"Config {args.config_name} uses non-16b external ports and is excluded from --pretest end-to-end testing"
            )

    print(f"Enumerated {len(configs)} unique thesis configurations")
    if skipped_configs:
        if args.pretest:
            print(f"Skipping {len(skipped_configs)} configs excluded by AHA sweep filters / non-16b external ports for --pretest")
        else:
            print(f"Skipping {len(skipped_configs)} configs excluded by AHA sweep filters")

    if not args.compile_only:
        generated = generate_all_collateral(args.output_dir, configs)
        print_collateral_summary(generated)

        if args.generate_only:
            return

    if args.compile_only:
        # Reload collateral from files (new subdir layout)
        generated = []
        for cfg in configs:
            name = config_name(cfg)
            path = os.path.join(args.output_dir, name, "lake_collateral.json")
            # Fall back to old flat layout
            if not os.path.exists(path):
                path = os.path.join(args.output_dir, f"{name}.json")
            if os.path.exists(path):
                with open(path) as f:
                    coll = json.load(f)
                generated.append((cfg, name, path, coll))
            else:
                print(f"WARNING: collateral for {name} not found, skipping")

    if args.pretest:
        runtime_modes = parse_runtime_modes(args.runtime_modes)
        results_csv = args.results_csv or os.path.join(args.output_dir, "pretest_results.csv")
        prior_rows, passed_pairs = ([], set())
        if args.resume:
            prior_rows, passed_pairs = load_prior_results(results_csv)
            prior_rows = [r for r in prior_rows if r.get("runtime_mode") in runtime_modes]
            passed_pairs = {p for p in passed_pairs if p[1] in runtime_modes}
            print(f"Resume: loaded {len(prior_rows)} prior rows, {len(passed_pairs)} PASS pairs will be skipped")
        results = run_pretest_sweep(
            generated=generated,
            aha_dir=args.aha_dir,
            app_name=args.app_name,
            app_dir=args.app_dir,
            output_dir=args.output_dir,
            runtime_modes=runtime_modes,
            width=args.width,
            height=args.height,
            glb_tile_mem_size=args.glb_tile_mem_size,
            results_csv=results_csv,
            prior_rows=prior_rows,
            passed_pairs=passed_pairs,
        )
        print_pretest_results_table(results)
    else:
        results = run_sweep(generated, args.app_dir, args.clockwork_path, args.output_dir)
        print_results_table(results)


if __name__ == "__main__":
    main()
