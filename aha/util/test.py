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
    parser.add_argument("--sparse-test-name", type=str, default=None)
    parser.add_argument("--sparse-comparison", type=str, default=None)
    parser.add_argument("--dense-fp", action="store_true")
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

def dispatch(args, extra_args=None):
    assert len(args.app) > 0
    env = os.environ.copy()
    app_args = []
    for idx, app in enumerate(args.app):
        # this is how many apps we 're running
        arg_name = f"APP{idx}"
        # get the full path of the app
        arg_path = f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{app}"
        app_args.append(f"+{arg_name}={arg_path}")

    app_args = " ".join(app_args)
    env["APP_ARGS"] = app_args
    if args.waveform:
        env["WAVEFORM"] = "1"
    elif args.waveform_glb:
        env["WAVEFORM_GLB_ONLY"] = "1"
    
    # if there are more than 1 app, store the log in the first app
    app_dir = Path(f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app[0]}")
    log_path = app_dir / Path("log")
    log_file_path = log_path / Path("aha_test.log")
    if args.log:
        subprocess.check_call(["mkdir", "-p", log_path])
        subprocess.check_call(["rm", "-f", log_file_path])

    if args.sparse:

        try:
            if args.run:
                subprocess_call_log (
                    cmd=["make", "run"] + extra_args,
                    cwd=str(args.aha_dir / "garnet" / "tests" / "test_app"),
                    env=env,
                    log=args.log,
                    log_file_path=log_file_path
                )
            else:
                subprocess_call_log (
                    cmd=["make", "sim"] + extra_args,
                    cwd=str(args.aha_dir / "garnet" / "tests" / "test_app"),
                    env=env,
                    log=args.log,
                    log_file_path=log_file_path
                )
        except:
            print("Failed as expected...move to offsite comparison...")

        from sam.onyx.generate_matrices import convert_aha_glb_output_file, get_tensor_from_files
        testname = args.sparse_test_name

        sparse_comp = args.sparse_comparison

        if sparse_comp is None:
            sparse_comp = f"/aha/garnet/SPARSE_TESTS/{testname}_0/GLB_DIR/{testname}_combined_seed_0/"


        tiles = 1
        # This is where we do the fallback comparison...
        # First get gold matrix from the output...

        name_line = None
        with open(f"{sparse_comp}/output_name.txt") as output_name_h_:
            name_line = output_name_h_.readlines()[0].strip()
        output_name = name_line
        assert output_name is not None

        # Find the output files...
        all_test_files_sim = os.listdir("/aha/garnet/tests/test_app/")
        just_out_files_sim = [file_ for file_ in all_test_files_sim if "tensor" in file_ and ".txt" in file_]
        for file__ in just_out_files_sim:
            convert_aha_glb_output_file(f"/aha/garnet/tests/test_app/{file__}", "/aha/garnet/SPARSE_TESTS/", tiles)
        for i in range(tiles):
            gold_matrix = numpy.load(f"{sparse_comp}/output_gold_{i}.npy")
            # Process according to the data type of the gold matrix 
            if gold_matrix.dtype == int:
                gold_matrix = gold_matrix.astype(numpy.uint16, casting='unsafe')
            elif gold_matrix.dtype == numpy.float32:
                # the gold matrix were already in bf16, no need to truncate again
                pass
            sim_matrix = get_tensor_from_files(name=output_name, files_dir="/aha/garnet/SPARSE_TESTS/",
                                                format="CSF",
                                                shape=gold_matrix.shape, base=16, early_terminate='x',
                                                use_fp=(gold_matrix.dtype == numpy.float32), suffix=f"_tile{i}").get_matrix()

            # Set up numpy so it doesn't print in scientific notation
            numpy.set_printoptions(suppress=True)
            print(f"GOLD")
            print(gold_matrix)
            print(f"SIM")
            print(sim_matrix)
        # for comparing floating point  
        assert numpy.allclose(gold_matrix, sim_matrix)

    else:

        if args.run:
            subprocess_call_log (
                cmd=["make", "run"] + extra_args,
                cwd=str(args.aha_dir / "garnet" / "tests" / "test_app"),
                env=env,
                log=args.log,
                log_file_path=log_file_path
            )
        else:
            subprocess_call_log (
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
            # load hex values as uint16 numpy array
            sim_array = numpy.array([int(value, 16) for line in hw_output for value in line.split()], dtype = numpy.uint16)

        # Then get the gold output generated by halide
        # Load meta config of dense app
        with open(f'{app_dir}/bin/design_meta.json') as design_meta_file:
            design_meta = json.load(design_meta_file)

        # Load gold output path
        assert len(design_meta["IOs"]["outputs"]) == 1, "There should be only one output file."
        gold_output_path = f'{app_dir}/bin/{design_meta["IOs"]["outputs"][0]["datafile"]}'
        assert os.path.exists(gold_output_path), f"The gold output file {gold_output_path} does not exist."

        # Load gold output array from raw file with big-endian
        gold_array = numpy.fromfile(gold_output_path, dtype='>u2')

        print(f"-------------- Dense Test Result --------------")

        assert gold_array.shape == sim_array.shape, "\033[91mThe shape of the gold and sim arrays do not match.\033[0m"

        if args.dense_fp:

            # define custom absolute tolerance for floating point comparison
            custom_atol = 1.5e-04 # default 1e-08
            custom_rtol = 1.0e-01 # default 1e-05
            sim_array_fp = numpy.array([bfbin2float(bin(x)[2:].zfill(16)) for x in sim_array], dtype = numpy.float32)
            gold_array_fp = numpy.array([bfbin2float(bin(y)[2:].zfill(16)) for y in gold_array], dtype = numpy.float32)

            # check diff array and print wrong pixels
            differences = numpy.abs(gold_array_fp - sim_array_fp)
            tolerances = custom_atol + custom_rtol * numpy.abs(sim_array_fp)
            exceed_indices = numpy.where(differences > tolerances)[0]
            max_diff = numpy.max(differences)
            if len(exceed_indices) > 0:
                print("Floating-point values exceeding tolerance:")
                for idx in exceed_indices[:20]:  # Limit to first 20 differences
                    actual_tolerance = custom_atol + custom_rtol * numpy.abs(sim_array_fp[idx])
                    print(f"Index: {idx}, Gold: {gold_array_fp[idx]}, Sim: {sim_array_fp[idx]}, Diff: {differences[idx]}, Allowed Tolerance: {actual_tolerance}")
                print(f"Total exceeding tolerance: {len(exceed_indices)}")
                print("The max absolute difference is:", max_diff)

            # save gold and sim array as npy files
            numpy.save(f'{app_dir}/bin/gold_output_array_fp.npy', gold_array_fp)
            numpy.save(f'{app_dir}/bin/sim_output_array_fp.npy', sim_array_fp)

            # assertion to enforce the check
            assert numpy.allclose(gold_array_fp, sim_array_fp, atol=custom_atol, rtol=custom_rtol), "\033[91mFloating point comparison failed.\033[0m"

            # print pass message and maximum difference
            print("\033[92mFloating point comparison passed.\033[0m")
            print("Max absolute difference is:", max_diff)

        else:

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
            assert numpy.array_equal(gold_array, sim_array), "\033[91mInteger comparison failed.\033[0m"
            print("\033[92mInteger comparison passed.\033[0m")
