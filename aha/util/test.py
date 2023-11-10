from pathlib import Path
import subprocess
import sys
import os
import numpy
from lassen.utils import float2bfbin, bfbin2float


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

        # This is where we do the fallback comparison...
        # First get gold matrix from the output...
        gold_matrix = numpy.load(f"{sparse_comp}/output_gold_0.npy")
        # Process according to the data type of the gold matrix 
        if gold_matrix.dtype == int:
            gold_matrix = gold_matrix.astype(numpy.uint16, casting='unsafe')
        elif gold_matrix.dtype == numpy.float32:
            # truncating to bfloat16 here again just to be extra extra save
            for idx, x in numpy.ndenumerate(gold_matrix):
                gold_matrix[idx] = bfbin2float(float2bfbin(x))

        name_line = None
        with open(f"{sparse_comp}/output_name.txt") as output_name_h_:
            name_line = output_name_h_.readlines()[0].strip()
        output_name = name_line
        assert output_name is not None

        # Find the output files...
        all_test_files_sim = os.listdir("/aha/garnet/tests/test_app/")
        just_out_files_sim = [file_ for file_ in all_test_files_sim if "tensor" in file_ and ".txt" in file_]
        for file__ in just_out_files_sim:
            convert_aha_glb_output_file(f"/aha/garnet/tests/test_app/{file__}", "/aha/garnet/SPARSE_TESTS/")
        # get_tensor_from_file returns the fibertree data structure, we want the data array itself
        # which can be obtained from FiberTree.get_matrix()
        sim_matrix = get_tensor_from_files(name=output_name, files_dir="/aha/garnet/SPARSE_TESTS/",
                                            format="CSF",
                                            shape=gold_matrix.shape, base=16, early_terminate='x',
                                            use_fp=(gold_matrix.dtype == numpy.float32)).get_matrix()

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

