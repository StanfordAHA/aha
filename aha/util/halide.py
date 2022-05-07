import copy
import os
import shutil
from pathlib import Path
import subprocess


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem)
    parser.add_argument("app")
    parser.add_argument("--sim", action='store_true')
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
    args.app = Path(args.app)
    env = copy.deepcopy(os.environ)
    env["COREIR_DIR"] = str(args.aha_dir / "coreir")
    env["COREIR_PATH"] = str(args.aha_dir / "coreir")
    env["LAKE_PATH"] = str(args.aha_dir / "lake")
    env["CLOCKWORK_PATH"] = str(args.aha_dir / "clockwork")
    halide_dir = args.aha_dir / "Halide-to-Hardware"
    app_dir = halide_dir / Path("apps/hardware_benchmarks") / args.app
    env["LAKE_CONTROLLERS"] = str(app_dir / "bin")
    env["LAKE_STREAM"] = str(app_dir / "bin")

    app_name = args.app.name
    run_sim = args.sim

    log_path = app_dir / Path("log")
    log_file_path = log_path / Path("aha_halide.log")
    if args.log:
        subprocess.check_call(["mkdir", "-p", log_path])
        subprocess.check_call(["rm", "-f", log_file_path])

    if "handcrafted" in str(args.app):
        # Generate pgm Images
        subprocess_call_log (
            cmd=["make", "-C", str(app_dir), "bin/input.raw", "bin/output_cpu.raw"],
            cwd=args.aha_dir / "Halide-to-Hardware",
            env=env,
            log=args.log,
            log_file_path=log_file_path
        )

        os.rename(
            app_dir / "bin/output_cpu.raw", app_dir / "bin/gold.raw",
        )
    
    else:
        # Raw Images
        subprocess_call_log (
            cmd=["make", "-C", str(app_dir), "compare", "bin/input_cgra.pgm", "bin/output_cgra_comparison.pgm"],
            cwd=args.aha_dir / "Halide-to-Hardware",
            env=env,
            log=args.log,
            log_file_path=log_file_path
        )

        os.rename(
            app_dir / "bin/input_cgra.pgm", app_dir / "bin/input.pgm",
        )
        os.rename(
            app_dir / "bin/output_cgra_comparison.pgm", app_dir / "bin/gold.pgm",
        )

    if run_sim:
        subprocess_call_log (
            cmd=["make", "-C", str(app_dir), "test-mem"],
            cwd=args.aha_dir / "Halide-to-Hardware",
            env=env,
            log=args.log,
            log_file_path=log_file_path
        )
    else:
        subprocess_call_log (
            cmd=["make", "-C", str(app_dir), "map"],
            cwd=args.aha_dir / "Halide-to-Hardware",
            env=env,
            log=args.log,
            log_file_path=log_file_path
        )

    #move to apps/bin
    clkwrk_design = app_name +"/" + app_name + "_garnet.json"
    if os.path.exists(str(app_dir / "bin/map_result"/ clkwrk_design)):
        shutil.copyfile(str(app_dir / "bin/map_result" / clkwrk_design), str(app_dir / "bin/design_top.json"))
