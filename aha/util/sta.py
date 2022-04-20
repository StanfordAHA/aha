from pathlib import Path
import os
import subprocess
import sys
import copy

def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app")
    parser.add_argument("--log", action="store_true")
    parser.set_defaults(dispatch=dispatch)


def subprocess_call_log(cmd, cwd, log, log_file_path):
    if log:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        subprocess.check_call(["tee", log_file_path, "-a"], stdin=proc.stdout)
        proc.wait()
    else:
        subprocess.check_call(
            cmd,
            cwd=cwd
        )


def dispatch(args, extra_args=None):
    args.app = Path(args.app)
    env = copy.deepcopy(os.environ)
    app_dir = Path(
        f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app}"
    )

    log_path = app_dir / Path("log")
    log_file_path = log_path / Path("aha_sta.log")
    if args.log:
        subprocess.check_call(["mkdir", "-p", log_path])
        subprocess.check_call(["rm", "-f", log_file_path])

    subprocess_call_log (
        cmd=[sys.executable, "sta.py", "-a", app_dir]  + extra_args,
        cwd=args.aha_dir / "archipelago/archipelago",
        log=args.log,
        log_file_path=log_file_path
    )

