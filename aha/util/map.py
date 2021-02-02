from pathlib import Path
import subprocess
import sys


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app")
    parser.add_argument("--base", default=None, type=str)
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    args.app = Path(args.app)

    if args.base is None:
        app_dir = Path(
            f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app}"
        )
    else:
        app_dir = (Path(args.base) / args.app).resolve()

    map_args = [
        "--interconnect-only",
        "--input-app",
        app_dir / "bin/design_top.json",
        "--input-file",
        app_dir / "bin/input.raw",
        "--output-file",
        app_dir / f"bin/{args.app.name}.bs",
        "--gold-file",
        app_dir / "bin/gold.raw",
    ]

    subprocess.check_call(
        [sys.executable, "garnet.py"] + map_args + extra_args,
        cwd=args.aha_dir / "garnet",
    )
