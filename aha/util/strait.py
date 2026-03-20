2.2.6
from pathlib import Path
import os
import shutil
import subprocess
import json


def add_subparser(subparser):
    parser = subparser.add_parser(
        Path(__file__).stem,
        description=(
            "AHA flow command for running voyager+strait compilation of a dense ML model (PyTorch -> protobuf -> CoreIR)."
        ),
    )
    parser.add_argument(
        "model",
        help="Dense ML model name to compile (e.g., bert, resnet18).",
    )
    parser.add_argument(
        "--gemm-datatype",
        default="int8",
        help="Datatype for GEMM ops (default: int8).",
    )
    parser.add_argument(
        "--non-gemm-datatype",
        default="bf16",
        help="Datatype for non-GEMM ops (default: bf16).",
    )
    parser.add_argument(
        "--mx-block-size",
        type=int,
        default=64,
        help="Microscaling block size (default: 64).",
    )
    parser.add_argument(
        "--mu-ic",
        type=int,
        default=64,
        help="Matrix unit input channels for hardware unrolling (default: 64).",
    )
    parser.add_argument(
        "--mu-oc",
        type=int,
        default=32,
        help="Matrix unit output channels for hardware unrolling (default: 32).",
    )
    parser.add_argument(
        "--unit-test",
        action="store_true",
        help="Compile a single unit-test op. Use customized unit_test PyTorch model if specified and model becomes the op in the unit test.",
    )
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    """
    Entry point for `aha strait`.

    Runs voyager-compiler (PyTorch -> protobuf) followed by strait (protobuf -> CoreIR) for the requested dense ML model.
    """
    model = args.model
    gemm_datatype = args.gemm_datatype
    non_gemm_datatype = args.non_gemm_datatype
    mx_block_size = args.mx_block_size
    mu_ic = args.mu_ic
    mu_oc = args.mu_oc
    is_unit_test = args.unit_test

    if hasattr(args, "aha_dir"):
        strait_path = os.path.join(str(args.aha_dir), "strait")
    else:
        strait_path = "/aha/strait"

    print(f"--- BEGIN aha strait {model}", flush=True)
    print(f"--- Using strait repo at {strait_path}", flush=True)

    _voyager_compile_full_model(
        model=model,
        strait_path=strait_path,
        gemm_datatype=gemm_datatype,
        non_gemm_datatype=non_gemm_datatype,
        mx_block_size=mx_block_size,
        mu_ic=mu_ic,
        mu_oc=mu_oc,
        is_unit_test=is_unit_test,
    )

    _strait_compile_full_model(
        model=model,
        gemm_datatype=gemm_datatype,
        strait_path=strait_path,
    )

    print(f"--- DONE aha strait {model}", flush=True)


def _voyager_compile_full_model(
    model: str,
    strait_path: str,
    gemm_datatype: str = "int8",
    non_gemm_datatype: str = "bf16",
    mx_block_size: int = 64,
    mu_ic: int = 64,
    mu_oc: int = 32,
    is_unit_test: bool = False,
):
    """
    Run voyager-compiler (PyTorch -> protobuf) for the given model.
    Creates a dedicated Python 3.10+ venv under strait_path so regression can stay on Python 3.8.
    """
    # Create a strictly isolated environment
    sanitized_env = os.environ.copy()
    sanitized_env.pop("VIRTUAL_ENV", None)  # Prevent parent venv inheritance
    sanitized_env.pop("PYTHONPATH", None)   # CRITICAL: Stop Python 3.8 packages from leaking into 3.13

    voyager_compiler_venv = os.path.join(strait_path, ".voyager-compiler-venv")
    voyager_python = os.path.join(voyager_compiler_venv, "bin", "python")

    # Ensure we have a Python 3.10+ venv.
    if not os.path.isfile(voyager_python):
        # Bypass the active 'aha' venv in this search.
        search_path = os.environ.get("PATH", "")
        if "VIRTUAL_ENV" in os.environ:
            active_venv_bin = os.path.join(os.environ["VIRTUAL_ENV"], "bin") + os.pathsep
            search_path = search_path.replace(active_venv_bin, "")

        for name in ("python3.12", "python3.11", "python3.10", "python3"):
            # Pass clean search_path here.
            candidate = shutil.which(name, path=search_path)
            if not candidate:
                continue
            try:
                out = subprocess.run(
                    [candidate, "-c", "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"],
                    capture_output=True,
                    timeout=5,
                )
                if out.returncode == 0:
                    break
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        else:
            raise RuntimeError(
                "[ERROR] voyager-compiler requires Python 3.10+. No suitable interpreter found on system PATH."
            )

        print(f"[INFO] Creating voyager-compiler venv at {voyager_compiler_venv} with {candidate}...", flush=True)

        # Use the sanitized env when creating the nested venv
        subprocess.check_call([candidate, "-m", "venv", voyager_compiler_venv], env=sanitized_env)

        voyager_python = os.path.join(voyager_compiler_venv, "bin", "python")

    # Install voyager-compiler into the venv if not already installed.
    voyager_compiler_install_path = os.path.join(strait_path, "voyager-compiler")
    print(f"\n[INFO] Ensuring voyager-compiler is installed in venv (using {voyager_python})...\n", flush=True)
    try:
        subprocess.run(
            [voyager_python, "-m", "pip", "show", "voyager-compiler"],
            check=True,
            capture_output=True,
            env=sanitized_env,
        )
    except subprocess.CalledProcessError:
        if os.path.isdir(voyager_compiler_install_path):
            print(f"[INFO] Installing voyager-compiler from {voyager_compiler_install_path}...", flush=True)
            subprocess.check_call(
                [voyager_python, "-m", "pip", "install", voyager_compiler_install_path],
                env=sanitized_env,
            )
        else:
            raise RuntimeError(
                f"[ERROR] voyager-compiler not installed and path not found: {voyager_compiler_install_path}"
            )

    # FIXME this is clearly not the right place for this
    print(f"\n[INFO] Hacking in a numpy fix until yuchen or somebody can do a better fix...\n", flush=True)
    subprocess.check_call(
        [voyager_python, "-m", "pip", "install", "-U", "numpy==2.2.6"],
        env=sanitized_env,
    )

    # ===============================
    # Run voyager compiler codegen.
    # ===============================
    print(f"\n[INFO] Running voyager compiler for full model {model}...\n", flush=True)
    test_model = "unit_test" if is_unit_test else model
    script_path = os.path.join(strait_path, "proto_frontend", "voyager_codegen.py")
    model_output_dir = os.path.join(strait_path, "proto_frontend", "_generated_protobuf", model, gemm_datatype)
    cmd = [
        voyager_python,
        script_path,
        test_model,
        "--activation",
        f"{gemm_datatype},qs=microscaling,bs={mx_block_size}",
        "--weight",
        f"{gemm_datatype},qs=microscaling,bs={mx_block_size}",
        "--force_scale_power_of_two",
        f"--{non_gemm_datatype}",
        "--model_output_dir",
        model_output_dir,
        "--hardware_unrolling",
        f"{mu_ic},{mu_oc}",
        "--dump_tensors",
        "--transform_layout",
        "--compile_single_layer",
    ]
    if is_unit_test:
        cmd.extend(["--unit_test_op", model])

    try:
        # Pass the sanitized environment to the final compilation step
        subprocess.check_call(cmd, cwd=strait_path, env=sanitized_env)
    except subprocess.CalledProcessError as e:
        print(
            f"\033[91mERROR: Voyager full-model compile failed: {e}\033[0m",
            flush=True,
        )
        raise


def _strait_compile_full_model(
    model: str,
    gemm_datatype: str,
    strait_path: str,
):
    """
    Run strait compilation (protobuf->coreir) for the given model.
    """

    # Clean model directory before compilation.
    output_dir = os.path.join(strait_path, "_generated_coreirs", model, gemm_datatype)
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)

    # First run scheduler to generate scheduled ops.
    from strait.proto_frontend.scheduler import protobuf_to_scheduled_ops

    model_protobuf_path = os.path.join(
        strait_path, "proto_frontend", "_generated_protobuf", model, gemm_datatype, "model.txt"
    )
    scheduled_ops_path = os.path.join(
        strait_path, "proto_frontend", "_generated_scheduled_ops", model, gemm_datatype, "scheduled_ops.json"
    )
    protobuf_to_scheduled_ops(model_protobuf_path, scheduled_ops_path)

    # Then run coreir backend to generate coreir json and tensor files.
    from strait.coreir_backend.coreir_backend import CoreIRBackend

    coreir_backend = CoreIRBackend(
        scheduled_ops_path=scheduled_ops_path,
        tensor_files_path=os.path.join(
            strait_path,
            "proto_frontend",
            "_generated_protobuf",
            model,
            gemm_datatype,
            "tensor_files",
        ),
        output_dir=output_dir,
    )
    coreir_backend.run()


def _strait_kernel_fp_output_map(model: str, gemm_datatype: str, strait_path: str):
    """
    Return a mapping {kernel_name: has_bfloat16_output}.
    Uses the scheduled_ops.json emitted by strait, which records per-kernel output datatypes.
    """
    sched_path = os.path.join(
        strait_path,
        "proto_frontend",
        "_generated_scheduled_ops",
        model,
        gemm_datatype,
        "scheduled_ops.json",
    )
    if not os.path.isfile(sched_path):
        return {}

    with open(sched_path, "r") as f:
        try:
            scheduled_ops = json.load(f)
        except Exception:
            return {}

    kernel_fp_map = {}
    for kernel in scheduled_ops:
        name = kernel.get("name")
        has_bf16 = any(
            out.get("datatype") == "bfloat16"
            for out in kernel.get("outputs", {}).values()
        )
        if name is not None:
            kernel_fp_map[name] = has_bf16
    return kernel_fp_map
