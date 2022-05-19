from pathlib import Path
import subprocess
import sys
import os


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app", nargs="+")
    parser.add_argument("--waveform", action="store_true")
    parser.add_argument("--waveform-glb", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--log", action="store_true")
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
    log_file_path = log_path / Path("aha_glb.log")
    if args.log:
        subprocess.check_call(["mkdir", "-p", log_path])
        subprocess.check_call(["rm", "-f", log_file_path])

    if args.run:
        subprocess_call_log (
            cmd=["make", "run"] + extra_args,
            cwd=str(args.aha_dir / "gem" / "tests" / "test_app"),
            env=env,
            log=args.log,
            log_file_path=log_file_path
        )
    else:
        subprocess_call_log (
            cmd=["make", "sim"] + extra_args,
            cwd=str(args.aha_dir / "gem" / "tests" / "test_app"),
            env=env,
            log=args.log,
            log_file_path=log_file_path
        )

