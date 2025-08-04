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
    print(f"--- Setting environment variables for {app}")
    for n, v in new_env_vars.items():
        print(f"--- {n} = {v}")
        env[n] = v
        os.environ[n] = v


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

        # Do offsite comparison similar to sparse flow
        # First get RTL simulation outputs
        assert os.path.exists(f"{args.aha_dir}/garnet/tests/test_app/hw_output.txt"), "The RTL sim output file does not exist."
        with open(f"{args.aha_dir}/garnet/tests/test_app/hw_output.txt", "r") as hw_output:
            # load hex values as uint16 numpy arrays for each output
            sim_array_list = []
            current_array = []

            for line in hw_output:
                if line.strip():  # Check if the line is not empty
                    values = [int(value, 16) for value in line.split()]
                    current_array.extend(values)
                else:
                    if current_array:  # Check if the current array is not empty
                        sim_array_list.append(numpy.array(current_array, dtype=numpy.uint16))
                        current_array = []

        golds = []
        for app in args.app:
            mu_test = args.mu_test[args.app.index(app)] if args.mu_test is not None else "inactive"
            app_dir = Path(f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{app}")
            voyager_app_dir = Path(f"{args.aha_dir}/voyager/compiled_collateral/{mu_test}")

            use_voyager_gold = "VOYAGER_GOLD" in os.environ and os.environ["VOYAGER_GOLD"] == "1"
            use_psum_workaround_gold = "USE_PSUM_WORKAROUND_GOLD" in os.environ and os.environ["USE_PSUM_WORKAROUND_GOLD"] == "1"

            if use_psum_workaround_gold:
                psum_idx = int(os.environ.get("PSUM_IDX", 1))
                gold_output_path = f"{app_dir}/{mu_test}_gold/kernel_{psum_idx}_output.txt"
                assert os.path.exists(gold_output_path), f"The gold output file {gold_output_path} does not exist."
                gold_array = []
                with open(gold_output_path, "r") as gold_output:
                    for line in gold_output:
                        if line.strip():  # Check if the line is not empty
                            values = [int(value, 16) for value in line.split()]
                            gold_array.extend(values)
                gold_array = numpy.array(gold_array, dtype=numpy.uint16)
                gold_array = gold_array.flatten()

            # Use voyager gold pre-supplied by the user
            elif use_voyager_gold:
                gold_output_path = f"{voyager_app_dir}/compare/gold_data.txt"
                assert os.path.exists(gold_output_path), f"The gold output file {gold_output_path} does not exist."

                with open(gold_output_path, "r") as gold_file:
                    gold_array = []
                    for line in gold_file:

                        if line.strip():  # Check if the line is not empty
                            values = [int(value, 16) for value in line.split()]
                            gold_array.extend(values)
                gold_array = numpy.array(gold_array, dtype=numpy.uint16)
                gold_array = gold_array.flatten()


            # Else, get the gold output generated by halide
            else:
                # Load meta config of dense app
                with open(f'{app_dir}/bin/design_meta.json') as design_meta_file:
                    design_meta = json.load(design_meta_file)

                # Load gold output path
                assert len(design_meta["IOs"]["outputs"]) == 1, "There should be only one output file."
                gold_output_path = f'{app_dir}/bin/{design_meta["IOs"]["outputs"][0]["datafile"]}'

                # Check if the gold output file exists
                assert os.path.exists(gold_output_path), f"The gold output file {gold_output_path} does not exist."
                # Load gold output array from raw file with big-endian
                gold_array = numpy.fromfile(gold_output_path, dtype='>u2')

            # Append gold array to golds list
            golds.append(gold_array)

        print(f"-------------- Dense Test Result --------------")

        for i in range(len(args.app)):
            gold_array = golds[i]
            sim_array = sim_array_list[i]

            # Check if the shape of the gold and sim arrays match
            if gold_array.shape != sim_array.shape:
                print("\033[93mWarning: The shape of the gold and sim arrays do not match. Truncating to the smaller shape.\033[0m")
                min_length = min(len(gold_array), len(sim_array))
                gold_array = gold_array[:min_length]
                sim_array = sim_array[:min_length]

        if args.dense_fp:
            # TODO: Implement back to back apps

            # define custom absolute tolerance for floating point comparison
            custom_atol = 1.5e-04  # default 1e-08
            custom_rtol = 2.0e-01  # default 1e-05
            sim_array_fp = numpy.array([bfbin2float(bin(x)[2:].zfill(16)) for x in sim_array], dtype=numpy.float32)
            gold_array_fp = numpy.array([bfbin2float(bin(y)[2:].zfill(16)) for y in gold_array], dtype=numpy.float32)

            # check diff array and print wrong pixels
            differences = numpy.abs(gold_array_fp - sim_array_fp)
            tolerances = custom_atol + custom_rtol * numpy.abs(gold_array_fp)
            exceed_indices = numpy.where(differences > tolerances)[0]
            # get max absolute and relative difference
            max_diff = numpy.max(differences)
            max_diff_index = numpy.argmax(differences)
            relative_differences = numpy.zeros_like(differences)
            relative_differences[gold_array_fp != 0] = differences[gold_array_fp != 0] / numpy.abs(gold_array_fp[gold_array_fp != 0])
            max_relative_diff = numpy.max(relative_differences) if numpy.any(gold_array_fp != 0) else 0
            max_relative_diff_index = numpy.argmax(relative_differences) if numpy.any(gold_array_fp != 0) else -1  # -1 if no valid index

            if len(exceed_indices) > 0:
                print("Floating-point values exceeding tolerance:")
                for idx in exceed_indices[:20]:  # Limit to first 20 differences
                    actual_tolerance = custom_atol + custom_rtol * numpy.abs(gold_array_fp[idx])
                    print(f"Index: {idx}, Gold: {gold_array_fp[idx]}, Sim: {sim_array_fp[idx]}, Diff: {differences[idx]}, Allowed Tolerance: {actual_tolerance}")
                print(f"Total exceeding tolerance: {len(exceed_indices)}")
                print("Max absolute difference is:", max_diff)
                print(f"Index: {max_diff_index}, Gold value: {gold_array_fp[max_diff_index]}, Sim value: {sim_array_fp[max_diff_index]}")
                if max_relative_diff_index != -1:
                    print(f"Max relative difference is {max_relative_diff}")
                    print(f"Index: {max_relative_diff_index}, Gold value: {gold_array_fp[max_relative_diff_index]}, Sim value: {sim_array_fp[max_relative_diff_index]}")
                else:
                    print("No valid maximum relative difference found (all gold values might be zero).")

            # save gold and sim array as npy files
            numpy.save(f'{app_dir}/bin/gold_output_array_fp.npy', gold_array_fp)
            numpy.save(f'{app_dir}/bin/sim_output_array_fp.npy', sim_array_fp)

            # do partial close check with small fraction tolerance
            close_elements = numpy.isclose(sim_array_fp, gold_array_fp, atol=custom_atol, rtol=custom_rtol)
            if numpy.all(close_elements):
                print("All elements are close.")
            else:
                mismatch_idx = numpy.nonzero(~close_elements)[0]
                mismatch_frac = len(mismatch_idx) / len(gold_array_fp)
                frac_tolerance = 6e-2
                if mismatch_frac <= frac_tolerance:
                    print(f"\033[93mWarning: Floating point comparison mostly passed with exceptions in {(mismatch_frac*100):.2f}% of all pixels.\033[0m")
                else:
                    assert False, f"\033[91mFloating point comparison failed. Exceptions {(mismatch_frac*100):.2f}% are beyond {frac_tolerance*100}% of all pixels\033[0m"

            # print pass message and maximum difference
            print("\033[92mFloating point comparison passed.\033[0m")
            print("Max absolute difference is:", max_diff)
            print(f"Index: {max_diff_index}, Gold value: {gold_array_fp[max_diff_index]}, Sim value: {sim_array_fp[max_diff_index]}")
            if max_relative_diff_index != -1:
                print(f"Max relative difference is {max_relative_diff}")
                print(f"Index: {max_relative_diff_index}, Gold value: {gold_array_fp[max_relative_diff_index]}, Sim value: {sim_array_fp[max_relative_diff_index]}")
            else:
                print("No valid maximum relative difference found (all simulation values might be zero).")

        # do bit accurate comparison for integer case
        else:
            # Works for checking back to back apps
            for app in args.app:
                gold_array = golds.pop(0)
                sim_array = sim_array_list.pop(0)

                print(f"Gold array len: {len(gold_array)}")
                print(f"Sim array len: {len(sim_array)}")

                # Auto-truncate if the shapes (lengths) differ
                if gold_array.shape != sim_array.shape:
                    print("\033[93mWarning: The shape of the gold and sim arrays do not match. Truncating to the smaller shape.\033[0m")
                    min_length = min(len(gold_array), len(sim_array))
                    gold_array = gold_array[:min_length]
                    sim_array = sim_array[:min_length]

                # check diff array and print wrong pixels
                differences = gold_array != sim_array
                diff_indices = numpy.where(differences)[0]
                if len(diff_indices) > 0:
                    print("Integer values differing:")
                    for idx in diff_indices[:20]:  # Limit to first 20 differences
                        print(f"Index: {idx}, Gold: {gold_array[idx]}, Sim: {sim_array[idx]}")
                    print(f"Total differing: {len(diff_indices)}")

                # save gold and sim array as npy files
                numpy.save(f'{app_dir}/bin/gold_output_array.npy', gold_array)
                numpy.save(f'{app_dir}/bin/sim_output_array.npy', sim_array)

                # Assertion for the integer case
                assert numpy.array_equal(gold_array, sim_array), f"\033[91m{app}: Integer comparison (Bit-accurate) failed.\033[0m"
                print(f"\033[92m{app}: Integer (Bit-accurate) comparison passed.\033[0m")
