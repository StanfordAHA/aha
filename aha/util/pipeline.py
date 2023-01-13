from pathlib import Path
import os
import subprocess
import sys
import copy
import json

def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app")
    parser.add_argument("--base", default=None, type=str)
    parser.add_argument("--no-parse", action="store_true")
    parser.add_argument("--log", action="store_true")
    parser.add_argument("--env-parameters", default="", type=str)
    parser.set_defaults(dispatch=dispatch)


def subprocess_call_log(cmd, cwd, env=None, log=False, log_file_path="log.log"):
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
            env=env,
            cwd=cwd
        )


def load_environmental_vars(env, app, env_parameters=None):
    filename = os.path.realpath(os.path.dirname(__file__)) + "/application_parameters.json"
    new_env_vars = {}

    if not os.path.exists(filename):
        print(f"{filename} not found, using default environmental variables")
    else:
        fin = open(filename, 'r')
        env_vars_fin = json.load(fin)
        if str(app) in env_vars_fin:
            if env_parameters is None or env_parameters not in env_vars_fin[str(app)]:
                new_env_vars = env_vars_fin[str(app)]["default"]
            else:
                new_env_vars = env_vars_fin[str(app)][env_parameters]

    for n, v in new_env_vars.items():
        env[n] = v



def dispatch(args, extra_args=None):
    args.app = Path(args.app)
    env = copy.deepcopy(os.environ)
    env["COREIR_DIR"] = str(args.aha_dir / "coreir")
    env["COREIR_PATH"] = str(args.aha_dir / "coreir")
    env["LAKE_PATH"] = str(args.aha_dir / "lake")
    env["CLOCKWORK_PATH"] = str(args.aha_dir / "clockwork")

    load_environmental_vars(env, args.app, str(args.env_parameters))

    if args.base is None:
        app_dir = Path(
            f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app}"
        )
    else:
        app_dir = (Path(args.base) / args.app).resolve()
    
    if os.path.exists(str(app_dir / "bin/input.raw")):
        ext = ".raw"
    else:
        ext = ".pgm"

    log_path = app_dir / Path("log")
    log_file_path = log_path / Path("aha_pipeline.log")

    if args.log:
        subprocess.check_call(["mkdir", "-p", log_path])
        subprocess.check_call(["rm", "-f", log_file_path])

    print (f"Using testbench file extension: {ext}.")

    map_args = [
        "--no-pd",
        "--interconnect-only",
        "--input-app",
        str(app_dir / "bin/design_top.json"),
        "--input-file",
        str(app_dir / f"bin/input{ext}"),
        "--output-file",
        str(app_dir / f"bin/{args.app.name}.bs"),
        "--gold-file",
        str(app_dir / f"bin/gold{ext}"),
        "--input-broadcast-branch-factor", "2",
        "--input-broadcast-max-leaves", "32",
        "--rv",
        "--sparse-cgra",
        "--sparse-cgra-combined",
        "--pipeline-pnr"
    ]

    subprocess_call_log (
        cmd=[sys.executable, "garnet.py"] + map_args + extra_args,
        cwd=args.aha_dir / "garnet",
        log=args.log,
        log_file_path=log_file_path,
        env=env
    )

    subprocess_call_log (
        cmd=["make", "-C", str(app_dir), "reschedule_mem"],
        cwd=args.aha_dir / "Halide-to-Hardware",
        env=env,
        log=args.log,
        log_file_path=log_file_path
    )

    map_args = [
        "--no-pd",
        "--interconnect-only",
        "--input-app",
        str(app_dir / "bin/design_top.json"),
        "--input-file",
        str(app_dir / f"bin/input{ext}"),
        "--output-file",
        str(app_dir / f"bin/{args.app.name}.bs"),
        "--gold-file",
        str(app_dir / f"bin/gold{ext}"),
        "--input-broadcast-branch-factor", "2",
        "--input-broadcast-max-leaves", "32",
        "--rv",
        "--sparse-cgra",
        "--sparse-cgra-combined",
        "--generate-bitstream-only"
    ]

    subprocess_call_log (
        cmd=[sys.executable, "garnet.py"] + map_args + extra_args,
        cwd=args.aha_dir / "garnet",
        log=args.log,
        log_file_path=log_file_path,
        env=env
    )

    # generate meta_data.json file
    if not args.no_parse:
        if not str(args.app).startswith("handcrafted"):
            # get the full path of the app
            arg_path = f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app}"
            subprocess_call_log (
                cmd=[sys.executable,
                 f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/hw_support/parse_design_meta.py",
                 "bin/design_meta_halide.json",
                 "--top", "bin/design_top.json",
                 "--place", "bin/design.place"],
                cwd=arg_path,
                log=args.log,
                log_file_path=log_file_path,
                env=env
            )

