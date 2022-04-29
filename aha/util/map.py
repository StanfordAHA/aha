from pathlib import Path
import os
import subprocess
import sys


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app")
    parser.add_argument("--base", default=None, type=str)
    parser.add_argument("--no-parse", action="store_true")
    parser.add_argument("--log", action="store_true")
    parser.set_defaults(dispatch=dispatch)


def subprocess_call_log(cmd, cwd, log, log_file_path):
    if log:
        print("[log] Command  : {}".format(cmd))
        print("[log] Log Path : {}".format(log_file_path), end="  ...", flush=True)
        with open(log_file_path, "a") as flog:
            subprocess.check_call(
                cmd,
                cwd=cwd,
                stdout=flog,
                stderr=flog
            )
        print("done")
    else:
        subprocess.check_call(
            cmd,
            cwd=cwd
        )


def dispatch(args, extra_args=None):
    args.app = Path(args.app)

    if args.base is None:
        app_dir = Path(
            f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app}"
        )
    else:
        app_dir = (Path(args.base) / args.app).resolve()

    #Resnet use pgm
    if os.path.exists(str(app_dir / "bin/input.raw")):
        ext = ".raw"
    else:
        ext = ".pgm"

    print (f"Using testbench file extension: {ext}.")

    map_args = [
        "--no-pd",
        "--interconnect-only",
        "--input-app",
        app_dir / "bin/design_top.json",
        "--input-file",
        app_dir / f"bin/input{ext}",
        "--output-file",
        app_dir / f"bin/{args.app.name}.bs",
        "--gold-file",
        app_dir / f"bin/gold{ext}",
    ]

    log_path = app_dir / Path("log")
    log_file_path = log_path / Path("aha_map.log")
    if args.log:
        subprocess.check_call(["mkdir", "-p", log_path])
        subprocess.check_call(["rm", "-f", log_file_path])

    subprocess_call_log (
        cmd=[sys.executable, "garnet.py"] + map_args + extra_args,
        cwd=args.aha_dir / "garnet",
        log=args.log,
        log_file_path=log_file_path
    )

    # generate meta_data.json file
    if not args.no_parse:
        if not str(args.app).startswith("handcrafted"):
            # get the full path of the app
            arg_path = f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app}"
            subprocess_call_log (
                [sys.executable,
                 f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/hw_support/parse_design_meta.py",
                 "bin/design_meta_halide.json",
                 "--top", "bin/design_top.json",
                 "--place", "bin/design.place"],
                cwd=arg_path,
                log=args.log,
                log_file_path=log_file_path
            )

