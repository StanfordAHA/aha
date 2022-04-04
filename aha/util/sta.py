from pathlib import Path
import os
import subprocess
import sys
import copy

def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app")
    parser.add_argument("--visualize", action="store_true")
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    args.app = Path(args.app)
    env = copy.deepcopy(os.environ)
    app_dir = Path(
        f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app}"
    )

    if not args.visualize:
        subprocess.check_call(
            [sys.executable, "-m", "archipelago.sta", "-a", app_dir]  + extra_args,
            cwd=args.aha_dir / "archipelago/archipelago",
        )
    else:
        subprocess.check_call(
            [sys.executable, "-m", "archipelago.sta", "-a", app_dir, "--visualize"]  + extra_args,
            cwd=args.aha_dir / "archipelago/archipelago",
        )

