import copy
import os
from pathlib import Path
import subprocess
import sys


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem)
    parser.add_argument("app")
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    args.app = Path(args.app)
    env = copy.deepcopy(os.environ)
    env["COREIR_DIR"] = str(args.aha_dir / "coreir")
    halide_dir = args.aha_dir / "Halide-to-Hardware"
    app_dir = halide_dir / Path("apps/hardware_benchmarks") / args.app

    # CoreIR Output
    subprocess.check_call(
        ["make", "-C", app_dir, "design-clockwork"],
        cwd=args.aha_dir / "Halide-to-Hardware",
        env=env,
    )

    # Raw Images
    subprocess.check_call(
        ["make", "-C", app_dir, "bin/input.raw", "bin/output_cpu.raw"],
        cwd=args.aha_dir / "Halide-to-Hardware",
        env=env,
    )

    os.rename(
        app_dir / "bin/output_cpu.raw", app_dir / "bin/gold.raw",
    )
