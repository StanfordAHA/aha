import copy
import os
import sys
import shutil
from pathlib import Path
import subprocess
import json


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, aliases=['halide'], description='AHA flow command for doing C simulation of a halide application, scheduling the application using Clockwork, and mapping it to PE and MEM tiles')
    parser.add_argument("app", help="Required parameter specifying which halide application to compile")
    parser.add_argument("--sim", action='store_true', help="Additionally runs the clockwork verilator simulation")
    parser.add_argument("--log", action="store_true", help="Creates a log for command output")
    parser.add_argument("--chain", action="store_true", help="Uses a chain structure for arithmetic reduction operations rather than a tree structure")
    parser.add_argument("--layer", type=str, help="Specifies layer parameters if running 'aha halide apps/resnet_output_stationary', options for LAYER are in application_parameters.json")
    parser.add_argument("--env-parameters", type=str, help="Specifies which environmental parameters to use from application_parameters.json, options for ENV_PARAMETERS are in application_parameters.json")
    parser.set_defaults(dispatch=dispatch)


def subprocess_call_log(cmd, cwd, env, log, log_file_path, use_shell=False):
    if log:
        print("[log] Command  : {}".format(" ".join(cmd)))
        print("[log] Log Path : {}".format(log_file_path), end="  ...", flush=True)
        with open(log_file_path, "a") as flog:
            subprocess.check_call(
                cmd,
                cwd=cwd,
                env=env,
                stdout=flog,
                stderr=flog,
                shell=use_shell
            )
        print("done")
    else:
        subprocess.check_call(
            cmd,
            cwd=cwd,
            env=env,
            shell=use_shell
        )


def load_environmental_vars(env, app, layer=None, env_parameters=None):
    filename = os.path.realpath(os.path.dirname(__file__)) + "/application_parameters.json"
    new_env_vars = {}
    app_name = str(app) if layer is None else str(layer)

    if not os.path.exists(filename):
        print(f"{filename} not found, not setting environmental variables")
    else:
        fin = open(filename, 'r')
        env_vars_fin = json.load(fin)
        if "global_parameters" in env_vars_fin:
            if env_parameters is None or str(env_parameters) not in env_vars_fin["global_parameters"]:
                new_env_vars.update(env_vars_fin["global_parameters"]["default"])
            else:
                new_env_vars.update(env_vars_fin["global_parameters"][str(env_parameters)])

        if app_name in env_vars_fin:
            if env_parameters is None or str(env_parameters) not in env_vars_fin[app_name]:
                new_env_vars.update(env_vars_fin[app_name]["default"])
            else:
                new_env_vars.update(env_vars_fin[app_name][str(env_parameters)])

    # We always set compute pipelining to 0 for dense ready-valid case
    if os.getenv("DENSE_READY_VALID") == "1":
        new_env_vars["PIPELINED"] = "0"

    print(f"--- Setting environment variables for {app}")
    for n, v in new_env_vars.items():
        print(f"--- {n} = {v}")
        env[n] = v


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

    load_environmental_vars(env, args.app, layer=args.layer, env_parameters=args.env_parameters)

    app_name = args.app.name
    run_sim = args.sim
    chain = args.chain

    log_path = app_dir / Path("log")
    log_file_path = log_path / Path("aha_map.log")
    if args.log:
        subprocess.check_call(["mkdir", "-p", log_path])
        subprocess.check_call(["rm", "-f", log_file_path])

    if "handcrafted" in str(args.app):
        # Generate pgm Images
        subprocess_call_log(
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
        subprocess_call_log(
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

    if not chain:
        subprocess_call_log(
            cmd=["make", "-C", str(app_dir), "tree"],
            cwd=args.aha_dir / "Halide-to-Hardware",
            env=env,
            log=args.log,
            log_file_path=log_file_path
        )

    if run_sim:
        subprocess_call_log(
            cmd=["make", "-C", str(app_dir), "test-mem"],
            cwd=args.aha_dir / "Halide-to-Hardware",
            env=env,
            log=args.log,
            log_file_path=log_file_path
        )
    else:
        subprocess_call_log(
            cmd=["make", "-C", str(app_dir), "map"],
            cwd=args.aha_dir / "Halide-to-Hardware",
            env=env,
            log=args.log,
            log_file_path=log_file_path
        )

    # move to apps/bin
    clkwrk_design = app_name + "/" + app_name + "_garnet.json"
    if os.path.exists(str(app_dir / "bin/map_result" / clkwrk_design)):
        shutil.copyfile(str(app_dir / "bin/map_result" / clkwrk_design), str(app_dir / "bin/design_top.json"))

    # Call voyager compiler where necessary
    is_voyager_app = False # TODO: just a placeholder for now. Will replace in near future with real condition check
    if is_voyager_app:
        # Create conda environment
        subprocess_call_log(
            cmd=["make", "create-env"],
            cwd=args.aha_dir / "voyager",
            env=env,
            log=args.log,
            log_file_path=log_file_path
        )

        # Set necessary env vars
        # PATH
        voyager_path = "/aha/voyager/VOYAGER_PATH.txt"
        if not os.path.isfile(voyager_path):
            sys.exit(f"Error: File '{voyager_path}' does not exist. It should have been generated during make create-env")
        with open(voyager_path, 'r') as f:
            first_line = f.readline().strip()
        os.environ['PATH'] = first_line
        print(f"PATH for voyager has been set to: {os.environ['PATH']}")

        # LD_LIBRARY_PATH
        conda_prefix = "/aha/voyager/.conda-env"
        ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
        new_ld_library_path = f"/cad/mentor/2024.2_2/Mgc_home/lib:/cad/mentor/2024.2_2/Mgc_home/shared/lib:{conda_prefix}/lib:{ld_library_path}"
        os.environ["LD_LIBRARY_PATH"] = new_ld_library_path
        print(f"LD_LIBRARY_PATH for voyager has been set to: {os.environ['LD_LIBRARY_PATH']}")

        # Other
        os.environ["PROJECT_ROOT"] = "/aha/voyager"
        os.environ["CODEGEN_DIR"] = "test/compiler"

        # Activate conda environment and run compiler. Deactivate when done
        print("Running voyager compiler...")

        # TODO: This cmd is just a placeholder example for now
        compile_cmd = "DATATYPE=MXINT8 IC_DIMENSION=64 OC_DIMENSION=32 CLOCK_PERIOD=5 python run_regression.py --models resnet18 --sims fast-systemc --num_processes 32 --tests conv2d_mx_default_6"

        os.system(
            f'bash -c \''
            f'cd /aha/voyager/ && '
            f'source ~/.bashrc && '
            f'source /cad/modules/tcl/init/bash && '
            f'module load catapult/2024.2_2 && '
            f'eval "$(conda shell.bash hook)" && '
            f'conda activate ./.conda-env && '
            f'{compile_cmd} && '
            f'module unload catapult/2024.2_2 && '
            f'conda deactivate\''
        )