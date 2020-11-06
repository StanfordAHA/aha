from pathlib import Path
import subprocess
import os


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app", nargs="+")
    parser.add_argument("--width", type=int, default=16)
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
    app_args = " ".join(app_args)
    env["APP_ARGS"] = app_args
    # figure out garnet.v path
    garnet_v = args.aha_dir / "garnet" / "garnet.v"
    assert os.path.isfile(garnet_v)
    env["CGRA_FILENAME"] = str(garnet_v)
    env["CGRA_WIDTH"] = str(args.width)

    # run the GLB simulation
    subprocess.check_call(
        ["make", "sim"] + extra_args,
        cwd=str(args.aha_dir / "garnet" / "virtualization"),
        env=env
    )
