from pathlib import Path
import subprocess
import os
import sys


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    # generate glb rtl
    if "--interconnect-only" not in extra_args:
        env = os.environ.copy()
        if "--width" in extra_args:
            idx = extra_args.index("--width")
            env["CGRA_WIDTH"] = str(extra_args[idx+1])
            subprocess.check_call(
                ["make", "rtl"],
                cwd=str(args.aha_dir / "garnet" / "global_buffer"),
                env=env
            )
    subprocess.check_call(
        [sys.executable, "garnet.py"] + extra_args, cwd=args.aha_dir / "garnet",
    )
