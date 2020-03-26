from pathlib import Path
import subprocess
import sys


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app")
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    args.app = Path(args.app)
    app_dir = Path(
        f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app}"
    )

    subprocess.check_call(
        [
            sys.executable,
            "tbg.py",
            "garnet.v",
            "garnet_stub.v",
            app_dir / f"bin/{args.app.name}.bs.json",
        ] + extra_args,
        cwd=args.aha_dir / "garnet",
    )
