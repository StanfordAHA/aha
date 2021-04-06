import copy
import os
import shutil
from pathlib import Path
import subprocess


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem)
    parser.add_argument("app")
    parser.add_argument("--sim", action='store_true')
    parser.set_defaults(dispatch=dispatch)


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
    if os.path.exists(str(app_dir / "bin/map_result"/ clkwrk_design)):
        shutil.move(str(app_dir / "bin/map_result" / clkwrk_design), str(app_dir / "bin/design_top.json"))

    # Raw Images
    subprocess.check_call(
        ["make", "-C", app_dir, "bin/input.raw", "bin/output_cpu.raw"],
        cwd=args.aha_dir / "Halide-to-Hardware",
        env=env,
    )

    os.rename(
        app_dir / "bin/output_cpu.raw", app_dir / "bin/gold.raw",
    )
