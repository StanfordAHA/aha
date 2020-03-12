from pathlib import Path
import subprocess
import sys


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    subprocess.check_call(
        [sys.executable, "garnet.py"] + extra_args, cwd=args.aha_dir / "garnet",
    )
