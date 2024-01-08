from pathlib import Path
import re
import json
import subprocess
import sys
import os
from tabulate import tabulate
import time
import tempfile


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("config")
    parser.add_argument("--env-parameters", default="", type=str)
    parser.set_defaults(dispatch=dispatch)


def buildkite_filter(s):
    return re.sub("^---", " ---", s, flags=re.MULTILINE)


def buildkite_call(command, env={}):
    env = {**os.environ.copy(), **env}
    app = subprocess.run(
        command,
        check=True,
        text=True,
        env=env,
    )


def gen_garnet(width, height):
    print("--- Generating Garnet", flush=True)
    start = time.time()
    if not os.path.exists("/aha/garnet/garnet.v"):
        buildkite_call(
            [
                "aha",
                "garnet",
                "--width", str(width),
                "--height", str(height),
                "--verilog",
                "--use_sim_sram",
                "--rv",
                "--sparse-cgra",
                "--sparse-cgra-combined",
                "--glb_tile_mem_size", str(128),
            ]
        )
    return time.time() - start


def generate_sparse_bitstreams(sparse_tests, width, height):
    if len(sparse_tests) == 0:
        return 0
    
    print(f"--- mapping all tests", flush=True)
    start = time.time()
    env_vars = {"PYTHONPATH": "/aha/garnet/"}
    start = time.time()
    all_sam_graphs = [f"/aha/sam/compiler/sam-outputs/onyx-dot/{testname}.gv" for testname in sparse_tests]

    buildkite_call(
        [
            "python",
            "/aha/garnet/tests/test_memory_core/build_tb.py",
            "--ic_fork",
            "--sam_graph", *all_sam_graphs,
            "--seed", f"{0}",
            "--dump_bitstream",
            "--add_pond",
            "--combined",
            "--pipeline_scanner",
            "--base_dir",
            "/aha/garnet/SPARSE_TESTS/",
            "--just_glb",
            "--dump_glb",
            "--fiber_access",
            #"--give_tensor",
            #"--tensor_locs",
            #"/aha/garnet/SPARSE_TESTS/MAT_TMP_DIR",
            "--width", str(width),
            "--height", str(height),
        ],
        env=env_vars,
    )
    time_map = time.time() - start
    return time_map


def test_sparse_app(testname, test=""):
    if test == "":
        test = testname

    print(f"--- {test}")

    env_vars = {"PYTHONPATH": "/aha/garnet/"}

    app_path = f"../../../garnet/SPARSE_TESTS/{testname}_0/GLB_DIR/{testname}_combined_seed_0"
    print(app_path, flush=True)

    try:
        subprocess.call(["make", "clean"], cwd=app_path)
    except:
        pass

    print(f"--- {test} - glb testing", flush=True)
    start = time.time()
    buildkite_call(
        ["aha", "test", app_path, "--sparse", "--sparse-test-name", testname], env=env_vars,
    )
    time_test = time.time() - start

    return 0, 0, time_test


def test_dense_app(test, width, height, layer=None, env_parameters=""):
    testname = layer if layer is not None else test
    print(f"--- {testname}")
    print(f"--- {testname} - compiling and mapping")
    app_path = "/aha/Halide-to-Hardware/apps/hardware_benchmarks/" + test
    print(app_path, flush=True)

    if layer is not None:
        layer_array = ["--layer", layer]
    else:
        layer_array = []

    try:
        subprocess.call(["make", "clean"], cwd=app_path)
    except:
        pass

    start = time.time()
    buildkite_call(["aha", "map", test, "--chain", "--env-parameters", env_parameters] + layer_array)
    time_compile = time.time() - start

    print(f"--- {testname} - pnr and pipelining", flush=True)
    start = time.time()

    buildkite_call(
        [
            "aha",
            "pnr",
            test,
            "--width", str(width),
            "--height", str(height),
            "--daemon", "auto",
            "--env-parameters", env_parameters,
        ] + layer_array
    )
    time_map = time.time() - start

    print(f"--- {testname} - glb testing", flush=True)
    start = time.time()
    buildkite_call(["aha", "test", test])
    time_test = time.time() - start

    return time_compile, time_map, time_test


def dispatch(args, extra_args=None):
    print(f"--- extra_args={extra_args}", flush=True)
    sparse_tests = []
    if args.config == "fast":
        width, height = 4, 4
        sparse_tests = [
            "vec_identity"
        ]
        glb_tests = [
            "apps/pointwise"
        ]
        resnet_tests = []
    elif args.config == "pr":
        width, height = 28, 16
        sparse_tests = [
            "matmul_ijk",
            "mat_mattransmul",
            "mat_sddmm",
            "vec_identity",
            "vec_elemadd",
            "vec_elemmul",
            "mat_mask_tri",
            "mat_vecmul_iter",
        ]
        glb_tests = [
            "apps/pointwise",
            "tests/ushift",
            "tests/arith",
            "tests/absolute",
            "tests/scomp",
            "tests/ucomp",
            "tests/uminmax",
            "tests/rom",
            "tests/conv_1_2",
            "tests/conv_2_1",
        ]
        resnet_tests = ["conv5_1"]
    elif args.config == "daily":
        width, height = 28, 16
        sparse_tests = [
            "vec_elemadd",
            "matmul_ikj",
            "vec_elemmul",
            "vec_identity",
            "vec_scalar_mul",
            "mat_elemadd",
            "mat_elemadd_relu",
            "mat_elemadd_leakyrelu_exp",
            "mat_elemadd3",
            "mat_elemmul",
            "mat_identity",
            "mat_mattransmul",
            "mat_sddmm",
            "tensor3_mttkrp",
            "tensor3_ttm",
            "tensor3_ttv",
            "mat_mask_tri",
            "mat_vecmul_iter",
            "matmul_ijk",
            "matmul_ijk_crddrop",
            "matmul_ijk_crddrop_relu",
            "spmm_ijk_crddrop",
            "spmm_ijk_crddrop_relu",
            "spmv",
            "spmv_relu",
            "masked_broadcast",
            "trans_masked_broadcast",
        ]
        glb_tests = [
            "apps/gaussian",
            "apps/pointwise",
            "apps/unsharp",
            "apps/camera_pipeline_2x2",
            "apps/harris_color",
            "apps/cascade",
            "apps/maxpooling",
            "tests/three_level_pond",
        ]
        resnet_tests = [
            "conv1",
            "conv4_1",
            "conv4_x",
            "conv5_x",
        ]
    elif args.config == "full":
        width, height = 28, 16
        sparse_tests = [
            "mat_elemadd",
            "mat_elemadd3",
            "mat_elemmul",
            "mat_identity",
            "mat_mattransmul",
            # Turned off until SUB ordering fixed in mapping
            # 'mat_residual',
            "mat_sddmm",
            "mat_vecmul_ij",
            "matmul_ijk",
            "matmul_jik",
            "tensor3_elemadd",
            "tensor3_elemmul",
            "tensor3_identity",
            "tensor3_innerprod",
            "tensor3_mttkrp",
            "tensor3_ttm",
            "tensor3_ttv",
            "vec_elemadd",
            "vec_elemmul",
            "vec_identity",
            "vec_scalar_mul",
            "mat_mask_tri",
            "mat_vecmul_iter",
        ]
        glb_tests = [
            "apps/pointwise",
            "tests/rom",
            "tests/arith",
            "tests/absolute",
            "tests/boolean_ops",
            "tests/equal",
            "tests/ternary",
            "tests/scomp",
            "tests/ucomp",
            "tests/sminmax",
            "tests/uminmax",
            "tests/sshift",
            "tests/ushift",
            "tests/conv_1_2",
            "tests/conv_2_1",
            "tests/conv_3_3",
            "apps/gaussian",
            "apps/brighten_and_blur",
            "apps/cascade",
            "apps/harris",
            "apps/resnet_layer_gen",
            "apps/unsharp",
            "apps/harris_color",
            "apps/camera_pipeline_2x2",
            "apps/maxpooling",
            "apps/matrix_multiplication"
        ]
        resnet_tests = [
            "conv1",
            "conv2_x",
            "conv3_1",
            "conv3_x",
            "conv4_1",
            "conv4_x",
            "conv5_1",
            "conv5_x",
        ]
    elif args.config == "resnet":
        width, height = 28, 16
        sparse_tests = []
        glb_tests = []
        resnet_tests = [
            "conv1",
            "conv2_x",
            "conv3_1",
            "conv3_x",
            "conv4_1",
            "conv4_x",
            "conv5_1",
            "conv5_x",
        ]

    else:
        raise NotImplementedError(f"Unknown test config: {args.config}")


    print(f"--- Running regression: {args.config}", flush=True)
    info = []
    t = gen_garnet(width, height)
    info.append(["garnet", t])

    generate_sparse_bitstreams(sparse_tests, width, height)

    for test in sparse_tests:
        t0, t1, t2 = test_sparse_app(test)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in glb_tests:
        t0, t1, t2 = test_dense_app(test, width, height, env_parameters=str(args.env_parameters))
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in resnet_tests:
        t0, t1, t2 = test_dense_app("apps/resnet_output_stationary", width, height, layer=test, env_parameters=str(args.env_parameters))
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
        
    print(f"+++ TIMING INFO", flush=True)
    print(tabulate(info, headers=["step", "total", "compile", "map", "test"]), flush=True)


def gather_tests(tags):
    pass
