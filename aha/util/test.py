from pathlib import Path
import subprocess
import sys
import os
import numpy
import json


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, aliases=['glb'], add_help=False)
    parser.add_argument("app", nargs="+")
    parser.add_argument("--waveform", action="store_true")
    parser.add_argument("--waveform-glb", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--log", action="store_true")
    parser.add_argument("--sparse", action="store_true")
    parser.add_argument("--dense-fp", action="store_true")
    parser.add_argument("--multiles", type=int, default=None)
    parser.add_argument("--dpr", action="store_true")
    parser.add_argument("--mu-test", nargs="+", type=str, help="Specifies the test to run on the external voyager matrix unit. If not specified, or specified as \"inactive\", the test is skipped.")
    parser.add_argument("--voyager-cgra-test", type=str, help="Specifies a standalone vector unit test. If not specified, the test will not be run.")
    parser.add_argument("--layer", type=str, help="Specifies layer parameters if running 'aha halide apps/resnet_output_stationary', options for LAYER are in application_parameters.json")
    parser.set_defaults(dispatch=dispatch)


def subprocess_call_log(cmd, cwd, env, log, log_file_path):
    if log:
        print("[log] Command  : {}".format(" ".join(cmd)))
        print("[log] Log Path : {}".format(log_file_path), end="  ...", flush=True)
        with open(log_file_path, "a") as flog:
            subprocess.check_call(
                cmd,
                cwd=cwd,
                env=env,
                stdout=flog,
                stderr=flog
            )
        print("done")
    else:
        subprocess.check_call(
            cmd,
            cwd=cwd,
            env=env
        )


# Same as lassen.util but have to redefine it here due to CI venv errors
def bfbin2float(bfstr):
    sign = bfstr[0]
    exp = bfstr[1:9]
    lfrac = bfstr[9:16]
    if sign == "0" and exp == "11111111" and lfrac != "0000000":
        return float('nan')
    elif sign == "1" and exp == "11111111" and lfrac != "0000000":
        return -float('nan')
    elif sign == "0" and exp == "11111111" and lfrac == "0000000":
        return float('inf')
    elif sign == "1" and exp == "11111111" and lfrac == "0000000":
        return -float('inf')
    elif sign == "0" and exp == "00000000" and lfrac == "0000000":
        return float(0)
    elif sign == "1" and exp == "00000000" and lfrac == "0000000":
        return -float(0)
    else:
        mult = 1
        if sign == "1":
            mult = -1
        nexp = int(exp, 2) - 127
        if exp != 0:
            lfrac = "1" + lfrac
        else:
            lfrac = "0" + lfrac
        nfrac = int(lfrac, 2)
        return mult * nfrac * (2 ** (nexp - 7))


def load_environmental_vars(env, app, layer=None, env_parameters=None):
    filename = os.path.realpath(os.path.dirname(__file__)) + "/application_parameters.json"
    new_env_vars = {}
    app_name = str(app) if layer is None else str(layer)

    if not os.path.exists(filename):
        print(f"{filename} not found, not setting environmental variables")
    else:
        fin = open(filename, 'r')
        env_vars_fin = json.load(fin)
        if "global_parameters" in env_vars_fin:
            if env_parameters is None or str(env_parameters) not in env_vars_fin["global_parameters"]:
                new_env_vars.update(env_vars_fin["global_parameters"]["default"])
            else:
                new_env_vars.update(env_vars_fin["global_parameters"][str(env_parameters)])

        if app_name in env_vars_fin:
            if env_parameters is None or str(env_parameters) not in env_vars_fin[app_name]:
                new_env_vars.update(env_vars_fin[app_name]["default"])
            else:
                new_env_vars.update(env_vars_fin[app_name][str(env_parameters)])

    # No need for each var to have its own '---' group, just use '+++' instead of '---'
    print(f"--- Setting environment variables for {app}")
    for n, v in new_env_vars.items():
        print(f"... {n} = {v}")
        env[n] = v
        os.environ[n] = v


def unpack_output(arr):
    # Ensure array is uint16
    arr = numpy.asarray(arr, dtype=numpy.uint16)

    # Extract lower and upper 8 bits
    lower = arr & 0xFF
    upper = (arr >> 8) & 0xFF

    # Interleave lower first, then upper
    result = numpy.empty(arr.size * 2, dtype=numpy.uint16)
    result[0::2] = lower
    result[1::2] = upper

    return result


def stream_gold_to_tb_layout(app_dir, output, gold):
    """Reorder a clockwork gold (bin/<out>.raw) from program order into the layout the testbench reads back.

    The clockwork testscript dumps the output in the order the program writes it. The testbench
    reads each output IO tile's GLB block back in address order, where that tile's in2glb pattern
    (write_data_stride over extent) stored its k-th token, and interleaves the tiles (element
    j + N*addr for tile j of N). The two agree when every tile stores its tokens sequentially and
    the program writes the tiles round-robin. Tiled outputs (a matmul output tile held in a pond)
    store with a scatter pattern, and outputs written by sequential per-tile loop nests (resnet's
    unrolled w) are tile-major in program order. The prog clockwork compiles (bin/*_memory.cpp)
    gives the program order of every output store, and an IO tile's name gives the op feeding it.
    Returns the reordered gold, or None when the layouts already agree or can't be resolved.
    """
    import glob
    import re

    tiles = output.get("io_tiles", [])
    if not tiles or any(t.get("E64_packed") or t.get("bank_toggle_mode") or t.get("extent_multiplier", 1) != 1
                        or t["addr"].get("E64_packed") or t["addr"].get("bank_toggle_mode")
                        or t["addr"].get("extent_multiplier", 1) != 1 for t in tiles):
        return None

    loops, ops, children, stores = {}, {}, {"prg": []}, {}
    add_output = f'prg.add_output("{output["name"]}");'
    for path in glob.glob(f"{app_dir}/bin/*_memory.cpp"):
        with open(path) as f:
            lines = f.read().splitlines()
        if not any(line.strip() == add_output for line in lines):
            continue
        for line in lines:
            m = re.match(r'\s*auto (\w+) = (\w+)(?:->|\.)add_loop\("\w+", (-?\d+), (-?\d+)\);', line)
            if m:
                var, parent, lo, hi = m.groups()
                loops[var] = int(hi) - int(lo)
                children.setdefault(parent, []).append(var)
                continue
            m = re.match(r'\s*auto (\w+) = (\w+)(?:->|\.)add_op\("(\w+)"\);', line)
            if m:
                ops[m.group(1)] = m.group(3)
                children.setdefault(m.group(2), []).append(m.group(1))
                continue
            m = re.match(r'\s*(\w+)->add_store\("' + re.escape(output["name"]) + r'",', line)
            if m:
                stores[m.group(1)] = stores.get(m.group(1), 0) + 1
        break
    if not stores:
        return None

    # Program order: a token's key is (position under parent, iteration) per enclosing loop, then the
    # op's position and the store's position inside the op. Its place in the testbench readback comes
    # from the IO tile fed by that store: the k-th token goes to sum(idx_d(k) * write_data_stride_d).
    n_tiles = len(tiles)
    keys, places = [], []
    def walk(var, path):
        for pos, child in enumerate(children.get(var, [])):
            if child in loops:
                walk(child, path + [(pos, loops[child])])
                continue
            for s in range(stores.get(child, 0)):
                j = [i for i, t in enumerate(tiles) if t["name"].endswith(f"_{ops[child]}_write_{s}")]
                if len(j) != 1:
                    raise ValueError(f"no IO tile for {ops[child]} store {s}")
                addr = tiles[j[0]]["addr"]
                dims = addr["dimensionality"]
                extent, stride = addr["extent"][:dims], addr["write_data_stride"][:dims]
                n = int(numpy.prod([e for _, e in path]))
                if int(numpy.prod(extent)) != n:
                    raise ValueError(f"IO tile extent {extent} != {n} tokens")
                k, a = numpy.arange(n), numpy.zeros(n, dtype=numpy.int64)
                for e, st in zip(extent, stride):
                    a += (k % e) * st
                    k = k // e
                places.append(a if n_tiles == 1 else j[0] + n_tiles * a)
                grids = numpy.meshgrid(*[numpy.arange(e) for _, e in path], indexing="ij")
                key = [c for (p, _), g in zip(path, grids) for c in (numpy.full(g.shape, p), g)]
                keys.append(numpy.stack([c.ravel() for c in key] + [numpy.full(n, pos), numpy.full(n, s)], axis=1))
    try:
        walk("prg", [])
    except (ValueError, KeyError):
        return None
    if not keys:
        return None

    width = max(k.shape[1] for k in keys)
    keys = numpy.concatenate([numpy.pad(k, ((0, 0), (0, width - k.shape[1])), constant_values=-1) for k in keys])
    place = numpy.concatenate(places)[numpy.lexsort(keys.T[::-1])]
    if len(place) != len(gold) or place.min() < 0 or place.max() >= len(gold) \
            or not numpy.all(numpy.bincount(place, minlength=len(gold)) == 1):
        return None
    if numpy.array_equal(place, numpy.arange(len(gold))):
        return None
    reordered = numpy.empty_like(gold)
    reordered[place] = gold
    return reordered


def dispatch(args, extra_args=None):
    assert len(args.app) > 0
    if args.mu_test is not None and len(args.mu_test) > 0:
        assert len(args.app) == len(args.mu_test), "If using --mu_tests, number of apps and mu tests must match."
    env = os.environ.copy()
    app_args = []
    for idx, app in enumerate(args.app):
        load_environmental_vars(env, app, layer=args.layer)
        # this is how many apps we 're running
        arg_name = f"APP{idx}"
        # get the full path of the app
        if not args.sparse:
            arg_path = f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{app}"
        else:
            arg_path = f"{args.aha_dir}/garnet/SPARSE_TESTS/{app}"
        app_args.append(f"+{arg_name}={arg_path}")

        if args.mu_test is not None and len(args.mu_test) > 0:
            mu_test = args.mu_test[idx]
            if mu_test != "inactive":
                mu_test_path = f"{args.aha_dir}/voyager/compiled_collateral/{mu_test}"
                app_args.append(f"+MU_TEST{idx}={mu_test_path}")
            else:
                app_args.append(f"+MU_TEST{idx}=inactive")

    if args.dpr is True:
        app_args.append(f"+DPR=1")

    app_args = " ".join(app_args)
    env["APP_ARGS"] = app_args
    if args.waveform:
        env["WAVEFORM"] = "1"
    elif args.waveform_glb:
        env["WAVEFORM_GLB_ONLY"] = "1"

    # if there are more than 1 app, store the log in the first app
    if not args.sparse:
        app_dir = Path(f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app[0]}")
    else:
        app_dir = Path(f"{args.aha_dir}/garnet/SPARSE_TESTS/{args.app[0]}")
    log_path = app_dir / Path("log")
    log_file_path = log_path / Path("aha_test.log")
    if args.log:
        subprocess.check_call(["mkdir", "-p", log_path])
        subprocess.check_call(["rm", "-f", log_file_path])

    if args.sparse:

        try:

            subprocess_call_log(
                cmd=["make", "clean_sparse_outputs"],
                cwd=str(args.aha_dir / "garnet" / "tests" / "test_app"),
                env=env,
                log=args.log,
                log_file_path=log_file_path
            )

            if args.run:
                subprocess_call_log(
                    cmd=["make", "run"] + extra_args,
                    cwd=str(args.aha_dir / "garnet" / "tests" / "test_app"),
                    env=env,
                    log=args.log,
                    log_file_path=log_file_path
                )
            else:
                subprocess_call_log(
                    cmd=["make", "sim"] + extra_args,
                    cwd=str(args.aha_dir / "garnet" / "tests" / "test_app"),
                    env=env,
                    log=args.log,
                    log_file_path=log_file_path
                )
        except:
            print("Failed as expected...move to offsite comparison...")

        from sam.onyx.generate_matrices import convert_aha_glb_output_file, get_tensor_from_files

        sparse_comp = str(app_dir)
        batches = len(args.app)

        tiles = 1
        if args.multiles:
            tiles = args.multiles
        # This is where we do the fallback comparison...
        # First get gold matrix from the output...

        name_line = None
        with open(f"{sparse_comp}/output_name.txt") as output_name_h_:
            name_line = output_name_h_.readlines()[0].strip()
        output_name = name_line
        assert output_name is not None

        output_mode_map = None
        with open(f"{sparse_comp}/output_mode_map.json") as output_mode_map_h_:
            output_mode_map = json.load(output_mode_map_h_)
        assert output_mode_map is not None

        # Find the output files...
        all_test_files_sim = os.listdir("/aha/garnet/tests/test_app/")
        just_out_files_sim = [file_ for file_ in all_test_files_sim if "tensor" in file_ and ".txt" in file_]
        for file__ in just_out_files_sim:
            convert_aha_glb_output_file(f"/aha/garnet/tests/test_app/{file__}", "/aha/garnet/SPARSE_TESTS/", tiles, batches)
        for j in range(batches):
            for i in range(tiles):
                gold_matrix = numpy.load(f"/aha/garnet/SPARSE_TESTS/{args.app[j]}/output_gold_{i}.npy")
                # Process according to the data type of the gold matrix
                if gold_matrix.dtype == int:
                    gold_matrix = gold_matrix.astype(numpy.uint16, casting='unsafe')
                elif gold_matrix.dtype == numpy.float32:
                    # the gold matrix were already in bf16, no need to truncate again
                    pass
                sim_matrix = get_tensor_from_files(name=output_name, files_dir="/aha/garnet/SPARSE_TESTS/",
                                                   format="CSF",
                                                   shape=gold_matrix.shape, base=16, early_terminate='x',
                                                   use_fp=(gold_matrix.dtype == numpy.float32),
                                                   suffix=f"_batch{j}_tile{i}",
                                                   tensor_ordering=output_mode_map).get_matrix()

                # Rearrange the axes of the sim_matrix base on the tensor ordering of the app
                rearrng_axis = []
                for reorder_tup in output_mode_map:
                    rearrng_axis.append(reorder_tup[0])
                is_scalar = (rearrng_axis == [])
                if not is_scalar:
                    sim_matrix = numpy.transpose(sim_matrix, rearrng_axis)

                # Set up numpy so it doesn't print in scientific notation
                numpy.set_printoptions(suppress=True)
                print("Batch: ", j, "Tile: ", i)
                # for comparing floating point
                if numpy.allclose(gold_matrix, sim_matrix):
                    print(f"Check Passed.")
                else:
                    print(f"GOLD")
                    print(gold_matrix)
                    print(f"SIM")
                    print(sim_matrix)
                    assert numpy.allclose(gold_matrix, sim_matrix), f"Check Failed.\n"

    else:

        if args.run:
            subprocess_call_log(
                cmd=["make", "run"] + extra_args,
                cwd=str(args.aha_dir / "garnet" / "tests" / "test_app"),
                env=env,
                log=args.log,
                log_file_path=log_file_path
            )
        else:
            subprocess_call_log(
                cmd=["make", "sim"] + extra_args,
                cwd=str(args.aha_dir / "garnet" / "tests" / "test_app"),
                env=env,
                log=args.log,
                log_file_path=log_file_path
            )

        # Helper function to load hex txt files into uint16 arrays
        def _load_hex_txt(txt_path: str):
            assert os.path.exists(txt_path), f"The RTL sim output file {txt_path} does not exist."
            vals = []
            with open(txt_path, "r") as f:
                for line in f:
                    if line.strip():
                        vals.extend(int(v, 16) for v in line.split())
            return numpy.array(vals, dtype=numpy.uint16)

        # Build a list of (app, mu_test, output_file_name, gold_array, sim_array, app_dir)
        comparisons = []

        for app in args.app:
            mu_test = args.mu_test[args.app.index(app)] if args.mu_test is not None else "inactive"
            voyager_cgra_test = args.voyager_cgra_test
            app_dir = Path(f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{app}")
            if voyager_cgra_test is None or voyager_cgra_test == "":
                voyager_test_fullname = mu_test
            else:
                voyager_test_fullname = voyager_cgra_test
            voyager_app_dir = Path(f"{args.aha_dir}/voyager/compiled_collateral/{voyager_test_fullname}")

            use_voyager_gold = "VOYAGER_GOLD" in os.environ and os.environ["VOYAGER_GOLD"] == "1"
            use_psum_workaround_gold = "USE_PSUM_WORKAROUND_GOLD" in os.environ and os.environ["USE_PSUM_WORKAROUND_GOLD"] == "1"
            packed_outputs = "PACKED_OUTPUTS" in os.environ and os.environ["PACKED_OUTPUTS"] == "1"
            soft_integer_comparison = "SOFT_INTEGER_COMPARISON" in os.environ and os.environ["SOFT_INTEGER_COMPARISON"] == "1"

            design_meta_path = f"{app_dir}/bin/design_meta.json"
            assert os.path.exists(design_meta_path), f"Missing meta file: {design_meta_path}"
            with open(design_meta_path) as design_meta_file:
                design_meta = json.load(design_meta_file)
            outputs = design_meta.get("IOs", {}).get("outputs", [])
            assert len(outputs) >= 1, "There should be at least one output."
            golds_by_name = {}

            if use_psum_workaround_gold:
                psum_idx = int(os.environ.get("PSUM_IDX", 1))
                per_tensor_scaling = "PER_TENSOR_SCALING" in os.environ and os.environ["PER_TENSOR_SCALING"] == "1"
                if per_tensor_scaling:
                    gold_output_path = f"/aha/Halide-to-Hardware/apps/hardware_benchmarks/apps/zircon_psum_reduction_fp/per_tensor_{voyager_test_fullname}_gold/kernel_{psum_idx}_output.txt"
                else:
                    gold_output_path = f"{app_dir}/{voyager_test_fullname}_gold/kernel_{psum_idx}_output.txt"
                assert os.path.exists(gold_output_path), f"The gold output file {gold_output_path} does not exist."
                gold_array = []
                with open(gold_output_path, "r") as gold_output:
                    for line in gold_output:
                        if line.strip():  # Check if the line is not empty
                            values = [int(value, 16) for value in line.split()]
                            gold_array.extend(values)
                gold_array = numpy.array(gold_array, dtype=numpy.uint16)
                gold_array = gold_array.flatten()
                output_file_name = "hw_output"  # Assuming single output named hw_output for psum workaround
                golds_by_name[output_file_name] = gold_array

            # Use voyager gold pre-supplied by the user
            elif use_voyager_gold:
                for out in outputs:
                    datafile = out["datafile"]
                    output_file_name, ext = os.path.splitext(datafile)

                    if output_file_name == "hw_output":
                        gold_output_path = f"{voyager_app_dir}/compare/gold_activation.txt"
                    elif output_file_name == "hw_output_scale":
                        gold_output_path = f"{voyager_app_dir}/compare/gold_scale.txt"
                    else:
                        raise ValueError(f"Unexpected voyager gold output file name: {output_file_name}")

                    assert os.path.exists(gold_output_path), f"The gold output file {gold_output_path} does not exist."

                    with open(gold_output_path, "r") as gold_file:
                        gold_array = []
                        for line in gold_file:

                            if line.strip():  # Check if the line is not empty
                                values = [int(value, 16) for value in line.split()]
                                gold_array.extend(values)
                    gold_array = numpy.array(gold_array, dtype=numpy.uint16)
                    gold_array = gold_array.flatten()

                    golds_by_name[output_file_name] = gold_array

            # Else, get the gold output generated by halide
            else:
                for out in outputs:
                    datafile = out["datafile"]
                    output_file_name, ext = os.path.splitext(datafile)
                    assert ext == ".raw", f"Unexpected datafile ext for output: {datafile}"
                    gold_output_path = f"{app_dir}/bin/{datafile}"
                    assert os.path.exists(gold_output_path), f"The gold output file {gold_output_path} does not exist."
                    if packed_outputs:
                        golds_by_name[output_file_name] = unpack_output(numpy.fromfile(gold_output_path, dtype=">u2"))
                    else:
                        golds_by_name[output_file_name] = numpy.fromfile(gold_output_path, dtype=">u2")
                        # A gold already rewritten into the testbench layout by a pre-PnR hook carries this marker.
                        if not os.path.exists(f"{app_dir}/bin/.{datafile}.gold_interleaved"):
                            reordered = stream_gold_to_tb_layout(app_dir, out, golds_by_name[output_file_name])
                            if reordered is not None:
                                print(f"[{app}::{output_file_name}] Gold reordered from clockwork program order to the GLB readback layout")
                                golds_by_name[output_file_name] = reordered

            for out in outputs:
                datafile = out["datafile"]
                output_file_name, _ = os.path.splitext(datafile)
                sim_txt_path = f"{args.aha_dir}/garnet/tests/test_app/{output_file_name}.txt"
                if packed_outputs:
                    sim_array = unpack_output(_load_hex_txt(sim_txt_path))
                else:
                    sim_array = _load_hex_txt(sim_txt_path)
                assert output_file_name in golds_by_name, f"Missing gold for output '{output_file_name}'."
                gold_array = golds_by_name[output_file_name]

                comparisons.append({
                    "app": app,
                    "name": output_file_name,
                    "gold": gold_array,
                    "sim": sim_array,
                    "app_dir": app_dir
                })

        print(f"-------------- Dense Test Result --------------")

        for compare in comparisons:
            gold_array = compare["gold"]
            sim_array = compare["sim"]
            if gold_array.shape != sim_array.shape:
                print(f"\033[93mWarning:\033[0m {compare['app']}::{compare['name']} gold vs sim shapes differ "
                      f"({gold_array.shape} vs {sim_array.shape}). Truncating to smaller length.")
                min_length = min(len(gold_array), len(sim_array))
                compare["gold"] = gold_array[:min_length]
                compare["sim"] = sim_array[:min_length]

        if soft_integer_comparison:
            # Soft integer comparison per output (bit accurate within +/- 1)
            for compare in comparisons:
                app = compare["app"]
                app_dir = compare["app_dir"]
                name = compare["name"]
                gold_array = compare["gold"]
                sim_array = compare["sim"]

                print(f"[{app}::{name}] Gold array len: {len(gold_array)}")
                print(f"[{app}::{name}] Sim array len: {len(sim_array)}")

                if gold_array.shape != sim_array.shape:
                    print(f"\033[93mWarning:\033[0m {app}::{name} gold vs sim shapes differ after truncation guard.")

                hard_integer_differences = numpy.abs(gold_array.astype(int) - sim_array.astype(int)) > 1
                hard_diff_indices = numpy.where(hard_integer_differences)[0]
                num_hard_diff_tolerance = 3
                if len(hard_diff_indices) > 0:
                    print(f"[{app}::{name}] Integer values differing by more than 1:")
                    for idx in hard_diff_indices[:20]:
                        print(f"Index: {idx}, Gold: {gold_array[idx]}, Sim: {sim_array[idx]}")
                    print(f"Total differing by more than 1: {len(hard_diff_indices)}")

                # Create histogram of percentage differences for hard differences
                hard_diff_percentages = 100.0 * numpy.abs(gold_array[hard_diff_indices].astype(int) - sim_array[hard_diff_indices].astype(int)) / 127
                if len(hard_diff_percentages) > 0:
                    hist, bin_edges = numpy.histogram(hard_diff_percentages, bins=[0, 1, 5, 10, 20, 50, 100, 200, 500, 1000])
                    print(f"[{app}::{name}] Histogram of percentage differences for hard differences:")
                    for i in range(len(hist)):
                        print(f"  {bin_edges[i]:>7.1f}% - {bin_edges[i+1]:>7.1f}% : {hist[i]} occurrences")

                soft_integer_differences = numpy.abs(gold_array.astype(int) - sim_array.astype(int)) == 1
                soft_diff_indices = numpy.where(soft_integer_differences)[0]
                if len(soft_diff_indices) > 0:
                    print(f"[{app}::{name}] Integer values differing by 1:")
                    for idx in soft_diff_indices[:20]:
                        print(f"Index: {idx}, Gold: {gold_array[idx]}, Sim: {sim_array[idx]}")
                    print(f"Total differing by 1: {len(soft_diff_indices)}")

                numpy.save(f"{app_dir}/bin/gold_{name}_array.npy", gold_array)
                numpy.save(f"{app_dir}/bin/sim_{name}_array.npy", sim_array)

                assert len(hard_diff_indices) <= num_hard_diff_tolerance, f"\033[91m{app}::{name}: Integer comparison (Bit-accurate +/-1) failed.\033[0m"

                if len(hard_diff_indices) > 0:
                    print(f"\033[93m{app}::{name}: Integer comparison (Bit-accurate +/-1) had {len(hard_diff_indices)} hard differences but within tolerance.\033[0m")

                if len(soft_diff_indices) > 0:
                    mismatch_frac = len(soft_diff_indices) / len(gold_array) if len(gold_array) else 0.0
                    frac_tolerance = 2e-1
                    if mismatch_frac <= frac_tolerance:
                        print(f"\033[93m{app}::{name}: Integer comparison (Bit-accurate +/-1) mostly passed with exceptions in {(mismatch_frac*100):.2f}% of all pixels.\033[0m")
                    else:
                        assert False, f"\033[91m{app}::{name}: Integer comparison (Bit-accurate +/-1) failed. Exceptions {(mismatch_frac*100):.2f}% are beyond {frac_tolerance*100}% of all pixels\033[0m"
                else:
                    print(f"\033[92m{app}::{name}: Integer (Bit-accurate +/-1) comparison passed. All pixels match exactly.\033[0m")

        elif args.dense_fp:

            # Define custom absolute tolerance for floating point comparison
            custom_atol = 1.5e-04  # default 1e-08
            custom_rtol = 2.0e-01  # default 1e-05
            for compare in comparisons:
                app_dir = compare["app_dir"]
                gold_array = compare["gold"]
                sim_array = compare["sim"]

                sim_array_fp = numpy.array([bfbin2float(bin(x)[2:].zfill(16)) for x in sim_array], dtype=numpy.float32)
                gold_array_fp = numpy.array([bfbin2float(bin(y)[2:].zfill(16)) for y in gold_array], dtype=numpy.float32)

                differences = numpy.abs(gold_array_fp - sim_array_fp)
                tolerances = custom_atol + custom_rtol * numpy.abs(gold_array_fp)
                exceed_indices = numpy.where(differences > tolerances)[0]
                max_diff = float(numpy.max(differences)) if differences.size else 0.0
                max_diff_index = int(numpy.argmax(differences)) if differences.size else -1
                relative_differences = numpy.zeros_like(differences)
                mask = gold_array_fp != 0
                relative_differences[mask] = differences[mask] / numpy.abs(gold_array_fp[mask])
                max_relative_diff = float(numpy.max(relative_differences)) if numpy.any(mask) else 0.0
                max_relative_diff_index = int(numpy.argmax(relative_differences)) if numpy.any(mask) else -1

                if len(exceed_indices) > 0:
                    print(f"[{compare['app']}::{compare['name']}] Floating-point values exceeding tolerance:")
                    for idx in exceed_indices[:20]:
                        actual_tol = custom_atol + custom_rtol * abs(gold_array_fp[idx])
                        print(f"Index: {idx}, Gold: {gold_array_fp[idx]}, Sim: {sim_array_fp[idx]}, Diff: {differences[idx]}, Allowed Tolerance: {actual_tol}")
                    print(f"Total exceeding tolerance: {len(exceed_indices)}")
                    print("Max absolute difference is:", max_diff)
                    if max_diff_index != -1:
                        print(f"Index: {max_diff_index}, Gold value: {gold_array_fp[max_diff_index]}, Sim value: {sim_array_fp[max_diff_index]}")
                    if max_relative_diff_index != -1:
                        print(f"Max relative difference is {max_relative_diff}")
                        print(f"Index: {max_relative_diff_index}, Gold value: {gold_array_fp[max_relative_diff_index]}, Sim value: {sim_array_fp[max_relative_diff_index]}")
                    else:
                        print("No valid maximum relative difference found (all gold values might be zero).")

                numpy.save(f"{app_dir}/bin/gold_{compare['name']}_array_fp.npy", gold_array_fp)
                numpy.save(f"{app_dir}/bin/sim_{compare['name']}_array_fp.npy", sim_array_fp)

                close_elements = numpy.isclose(sim_array_fp, gold_array_fp, atol=custom_atol, rtol=custom_rtol)
                if numpy.all(close_elements):
                    print(f"\033[92m[{compare['app']}::{compare['name']}] Floating point comparison passed.\033[0m")
                else:
                    mismatch_idx = numpy.nonzero(~close_elements)[0]
                    mismatch_frac = len(mismatch_idx) / len(gold_array_fp) if len(gold_array_fp) else 0.0
                    frac_tolerance = 6e-2
                    if mismatch_frac <= frac_tolerance:
                        print(f"\033[93m[{compare['app']}::{compare['name']}] Floating point comparison mostly passed with exceptions in {(mismatch_frac*100):.2f}% of all pixels.\033[0m")
                    else:
                        assert False, f"\033[91m[{compare['app']}::{compare['name']}] Floating point comparison failed. Exceptions {(mismatch_frac*100):.2f}% are beyond {frac_tolerance*100}% of all pixels\033[0m"

                print("Max absolute difference is:", max_diff)
                if max_diff_index != -1:
                    print(f"Index: {max_diff_index}, Gold value: {gold_array_fp[max_diff_index]}, Sim value: {sim_array_fp[max_diff_index]}")
                if max_relative_diff_index != -1:
                    print(f"Max relative difference is {max_relative_diff}")
                    print(f"Index: {max_relative_diff_index}, Gold value: {gold_array_fp[max_relative_diff_index]}, Sim value: {sim_array_fp[max_relative_diff_index]}")
                else:
                    print("No valid maximum relative difference found (all simulation values might be zero).")

        else:
            # Integer bit-accurate comparison per output
            for compare in comparisons:
                app = compare["app"]
                app_dir = compare["app_dir"]
                name = compare["name"]
                gold_array = compare["gold"]
                sim_array = compare["sim"]

                print(f"[{app}::{name}] Gold array len: {len(gold_array)}")
                print(f"[{app}::{name}] Sim array len: {len(sim_array)}")

                if gold_array.shape != sim_array.shape:
                    print(f"\033[93mWarning:\033[0m {app}::{name} gold vs sim shapes differ after truncation guard.")

                differences = gold_array != sim_array
                diff_indices = numpy.where(differences)[0]
                if len(diff_indices) > 0:
                    print(f"[{app}::{name}] Integer values differing:")
                    for idx in diff_indices[:20]:
                        print(f"Index: {idx}, Gold: {gold_array[idx]}, Sim: {sim_array[idx]}")
                    print(f"Total differing: {len(diff_indices)}")

                numpy.save(f"{app_dir}/bin/gold_{name}_array.npy", gold_array)
                numpy.save(f"{app_dir}/bin/sim_{name}_array.npy", sim_array)

                assert numpy.array_equal(gold_array, sim_array), f"\033[91m{app}::{name}: Integer comparison (Bit-accurate) failed.\033[0m"
                print(f"\033[92m{app}::{name}: Integer (Bit-accurate) comparison passed.\033[0m")
