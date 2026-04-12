"""Sweep thesis experiment specs through clockwork compilation of conv_3_3.

Generates collateral JSON files for all unique hardware configurations from
lake's all_experiments_thesis.sh, then runs clockwork compilation against
each to determine which configs can successfully compile conv_3_3.

Usage:
    python -m aha.util.sweep_thesis_collateral [--generate-only] [--compile-only]
"""

import argparse
import glob as globmod
import itertools
import json
import math
import os
import shutil
import subprocess
import sys

from lake.spec.spec import Spec
from lake.spec.port import Port
from lake.spec.storage import SingleBankStorage
from lake.spec.memory_port import MemoryPort
from lake.spec.iteration_domain import IterationDomain
from lake.spec.address_generator import AddressGenerator
from lake.spec.schedule_generator import ScheduleGenerator
from lake.utils.spec_enum import Runtime, Direction, MemoryPortType


def build_spec(storage_capacity=4096, data_width=16, vec_width=4,
               dims=6, in_ports=2, out_ports=2, dual_port=False,
               vec_capacity=2, max_extent=None, max_sequence_width=None):
    """Factory function to build a lake Spec for any thesis configuration.

    Args:
        storage_capacity: SRAM capacity in bytes.
        data_width: External data width in bits.
        vec_width: Vector / fetch width (1 = no vectorization).
        dims: Number of iteration domain dimensions.
        in_ports: Number of input ports.
        out_ports: Number of output ports.
        dual_port: Whether to use separate R/W MemoryPorts (True) or shared RW (False).
        vec_capacity: Vector capacity for SIPO/PISO buffers.
        max_extent: Maximum iteration extent (affects counter upper bound).
        max_sequence_width: Maximum sequence width (affects stride width).

    Returns:
        A lake Spec instance.
    """
    id_width = 11
    if max_extent is not None:
        id_width = max(1, math.ceil(math.log2(max(max_extent, 2))))
    stride_width = 16
    if max_sequence_width is not None:
        stride_width = max(1, math.ceil(math.log2(max(max_sequence_width, 2))))

    ls = Spec(name="lakespec", opt_rv=False, remote_storage=False,
              config_passthru=False, comply_17=True)

    vc = vec_capacity if vec_width > 1 else None
    int_dw = data_width * vec_width

    # Create input ports
    input_port_list = []
    for _ in range(in_ports):
        p = Port(ext_data_width=data_width, int_data_width=int_dw,
                 vec_capacity=vc, runtime=Runtime.STATIC, direction=Direction.IN,
                 opt_rv=False, opt_timing=False)
        input_port_list.append(p)
    ls.register(*input_port_list)

    # Create output ports
    output_port_list = []
    for _ in range(out_ports):
        p = Port(ext_data_width=data_width, int_data_width=int_dw,
                 vec_capacity=vc, runtime=Runtime.STATIC, direction=Direction.OUT)
        output_port_list.append(p)
    ls.register(*output_port_list)

    # Create controllers for each port
    in_controllers = []
    for _ in range(in_ports):
        id_ = IterationDomain(dimensionality=dims, extent_width=id_width)
        ag_ = AddressGenerator(dimensionality=dims)
        sg_ = ScheduleGenerator(dimensionality=dims, stride_width=stride_width)
        ls.register(id_, ag_, sg_)
        in_controllers.append((id_, ag_, sg_))

    out_controllers = []
    for _ in range(out_ports):
        id_ = IterationDomain(dimensionality=dims, extent_width=id_width)
        ag_ = AddressGenerator(dimensionality=dims)
        sg_ = ScheduleGenerator(dimensionality=dims, stride_width=stride_width)
        ls.register(id_, ag_, sg_)
        out_controllers.append((id_, ag_, sg_))

    # Create storage and memory ports
    stg = SingleBankStorage(capacity=storage_capacity)
    if dual_port:
        write_mp = MemoryPort(data_width=data_width * vec_width,
                              mptype=MemoryPortType.W, delay=1)
        read_mp = MemoryPort(data_width=data_width * vec_width,
                             mptype=MemoryPortType.R, delay=1)
        ls.register(stg, write_mp, read_mp)
    else:
        shared_mp = MemoryPort(data_width=data_width * vec_width,
                               mptype=MemoryPortType.RW, delay=1)
        ls.register(stg, shared_mp)

    # Connect ports to controllers
    for i in range(in_ports):
        id_, ag_, sg_ = in_controllers[i]
        ls.connect(input_port_list[i], id_)
        ls.connect(input_port_list[i], ag_)
        ls.connect(input_port_list[i], sg_)

    for i in range(out_ports):
        id_, ag_, sg_ = out_controllers[i]
        ls.connect(output_port_list[i], id_)
        ls.connect(output_port_list[i], ag_)
        ls.connect(output_port_list[i], sg_)

    # Connect ports to memory ports
    if dual_port:
        for p in input_port_list:
            ls.connect(p, write_mp)
        for p in output_port_list:
            ls.connect(p, read_mp)
        ls.connect(write_mp, stg)
        ls.connect(read_mp, stg)
    else:
        for p in input_port_list:
            ls.connect(p, shared_mp)
        for p in output_port_list:
            ls.connect(p, shared_mp)
        ls.connect(shared_mp, stg)

    return ls


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
    parser.add_argument("--generate-only", action="store_true",
                        help="Only generate collateral, don't compile")
    parser.add_argument("--compile-only", action="store_true",
                        help="Only compile (assumes collateral already generated)")
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

    configs = enumerate_thesis_configs()
    print(f"Enumerated {len(configs)} unique thesis configurations")

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

    results = run_sweep(generated, args.app_dir, args.clockwork_path, args.output_dir)
    print_results_table(results)


if __name__ == "__main__":
    main()
