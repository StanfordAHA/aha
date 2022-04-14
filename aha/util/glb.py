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

def subprocess_check_call_log(cmd, cwd, env, log, log_path):
    if log:
        log_file_path = log_path + "/aha_glb.log"
        subprocess.check_call(["mkdir", "-p", log_path])
        subprocess.check_call(["rm", "-f", log_file_path])
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        subprocess.check_call(["tee", log_file_path], stdin=proc.stdout)
        proc.wait()
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

    if args.run:
        make_target = "run"
    else:
        make_target = "sim"

    run_cmd = ["make", make_target] + extra_args
    run_dir = str(args.aha_dir / "garnet" / "tests" / "test_app")

    log_path = arg_path + "/log"
    subprocess_check_call_log(
        cmd=run_cmd,
        cwd=run_dir,
        env=env,
        log=args.log,
        log_path=log_path
    )
