import copy
import os
import shutil
from pathlib import Path
import subprocess
import sys


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app")
    parser.add_argument("--base", default=None, type=str)
    parser.add_argument("--sim", action='store_true')
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    args.app = Path(args.app)

    env = copy.deepcopy(os.environ)
    env["COREIR_DIR"] = str(args.aha_dir / "coreir")
    env["COREIR_PATH"] = str(args.aha_dir / "coreir")
    env["LAKE_PATH"] = str(args.aha_dir / "lake")
    env["CLOCKWORK_PATH"] = str(args.aha_dir / "clockwork")

    if args.base is None:
        app_dir = Path(
            f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app}"
        )
    else:
        app_dir = (Path(args.base) / args.app).resolve()
    env["LAKE_CONTROLLERS"] = str(app_dir / "bin")
    env["LAKE_STREAM"] = str(app_dir / "bin")

    app_name = args.app.name

    run_sim = args.sim
    if run_sim:
        subprocess.check_call(
            ["make", "-C", app_dir, "test-mem"],
            cwd=args.aha_dir / "Halide-to-Hardware",
            env=env,
        )
    else:
        subprocess.check_call(
            ["make", "-C", app_dir, "mem"],
            cwd=args.aha_dir / "Halide-to-Hardware",
            env=env,
        )

        #move to apps/bin
        clkwrk_design = app_name +"/" + app_name + "_garnet.json"
        shutil.move(str(app_dir / "bin/map_result" / clkwrk_design), str(app_dir / "bin/design_top.json"))


        map_args = [
            "--no-pd",
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
