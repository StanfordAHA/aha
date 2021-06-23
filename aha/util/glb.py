from pathlib import Path
import subprocess
import sys
import os


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app", nargs="+")
    parser.add_argument("--width", type=int, default=16)
    parser.add_argument("--vcd", action="store_true")
    parser.add_argument("--vcd-glb", action="store_true")
    parser.set_defaults(dispatch=dispatch)


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
        # generate meta_data.json file
        subprocess.check_call(
            [sys.executable,
             f"../../hw_support/parse_design_meta.py",
             "bin/design_meta_halide.json",
             "--top", "bin/design_top.json",
             "--place", "bin/design.place"],
            cwd=arg_path
        )
    app_args = " ".join(app_args)
    env["APP_ARGS"] = app_args
    # figure out garnet.v path
    garnet_v = args.aha_dir / "garnet" / "garnet.v"
    assert os.path.isfile(garnet_v)
    env["CGRA_FILENAME"] = str(garnet_v)
    env["CGRA_WIDTH"] = str(args.width)
    if args.vcd:
        env["RUN_ARGS"] = "-input shm.tcl"
    elif args.vcd_glb:
        env["RUN_ARGS"] = "-input shm_glb.tcl"

    subprocess.check_call(
        ["make", "sim"] + extra_args,
        cwd=str(args.aha_dir / "garnet" / "tests" / "test_app"),
        env=env
    )
