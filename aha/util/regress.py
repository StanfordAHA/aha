from pathlib import Path
import re
import json
import subprocess
import sys
import os
from tabulate import tabulate
import time
from sam.onyx.generate_matrices import *
import tempfile
import glob
from collections import defaultdict
import shutil


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
    print("--- Generating Garnet")
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
            ]
        )
    return time.time() - start


def generate_sparse_bitstreams(sparse_tests, width, height):
    if len(sparse_tests) == 0:
        return 0
    
    print(f"--- mapping all tests")
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
    print(app_path)

    try:
        subprocess.call(["make", "clean"], cwd=app_path)
    except:
        pass

    print(f"--- {test} - glb testing")
    start = time.time()
    buildkite_call(
        ["aha", "test", app_path, "--sparse", "--sparse-test-name", testname], env=env_vars,
    )
    time_test = time.time() - start

    return 0, 0, time_test


def test_dense_app(test, width, height, env_parameters, extra_args, layer=None, dense_only=False, use_fp=False):
    env_parameters = str(env_parameters)
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

    # To use daemon, call regress.py with args '--daemon auto'
    # --- extra_args=['--daemon', 'auto']
    use_daemon = []
    if (extra_args):
        if ('--daemon' in extra_args) and ('auto' in extra_args):
            use_daemon = [ "--daemon", "auto" ]

    buildkite_args = [
            "aha",
            "pnr",
            test,
            "--width", str(width),
            "--height", str(height),
            "--env-parameters", env_parameters,
        ] + use_daemon + layer_array

    if dense_only:
        buildkite_args.append("--dense-only")
    
    buildkite_call(buildkite_args)

    time_map = time.time() - start

    print(f"--- {testname} - glb testing", flush=True)
    start = time.time()
    if use_fp:
        buildkite_call(["aha", "test", test, "--dense-fp"])
    else:
        buildkite_call(["aha", "test", test])
    time_test = time.time() - start

    return time_compile, time_map, time_test

def test_hardcoded_dense_app(test, width, height, env_parameters, extra_args, layer=None, dense_only=False):
    env_parameters = str(env_parameters)
    testname = layer if layer is not None else test
    print(f"--- {testname}")
    print(f"--- {testname} - skip compiling and mapping")
    app_path = "/aha/Halide-to-Hardware/apps/hardware_benchmarks/" + test
    print(app_path, flush=True)

    if layer is not None:
        layer_array = ["--layer", layer]
    else:
        layer_array = []

    start = time.time()
    time_compile = time.time() - start

    print(f"--- {testname} - pnr and pipelining", flush=True)
    start = time.time()
    try:
        subprocess.call(["make", "clean"], cwd=app_path)
    except:
        pass

    try:
        print(f"copying hardcoded bin folder", flush=True)
        shutil.copytree(f"{app_path}/bin_hardcoded", f"{app_path}/bin")
    except:
        print(f"please don't delete hardcoded bin folder", flush=True)

    # To use daemon, call regress.py with args '--daemon auto'
    # --- extra_args=['--daemon', 'auto']
    use_daemon = []
    if (extra_args):
        if ('--daemon' in extra_args) and ('auto' in extra_args):
            use_daemon = [ "--daemon", "auto" ]

    buildkite_args = [
                "aha",
                "pnr",
                test,
                "--width", str(width),
                "--height", str(height),
                "--generate-bitstream-only",
                "--env-parameters", env_parameters,
            ] + use_daemon + layer_array

    if dense_only:
        buildkite_args.append("--dense-only")

    buildkite_call(buildkite_args)

    time_map = time.time() - start

    print(f"--- {testname} - glb testing", flush=True)
    start = time.time()
    buildkite_call(["aha", "test", test])
    time_test = time.time() - start

    return time_compile, time_map, time_test

def dispatch(args, extra_args=None):
    sparse_tests = []
    if args.config == "fast":
        width, height = 32, 16
        sparse_tests = [
            # "vec_identity"
        ]
        glb_tests = [
            # "apps/pointwise",
            # "apps/glb_exchange",
        ]
        glb_tests_fp = [
            "apps/sequential_0_fp",
            # "apps/pointwise_fp",
            # "apps/relu_layer_fp",
            # "apps/depthwise_conv_preload_fp",
        ]
        resnet_tests = []
        resnet_tests_fp = []
        hardcoded_dense_tests = []
    elif args.config == "pr":
        width, height = 32, 16
        sparse_tests = [
            "vec_elemadd",
            "vec_elemmul",
            "vec_identity",
            "vec_scalar_mul",
            "mat_vecmul_ij",
            "mat_elemadd",
            "mat_elemadd_relu",
            "matmul_ijk",
            "matmul_ijk_crddrop",
            "matmul_ijk_crddrop_relu",
            # Turned off until SUB ordering fixed in mapping
            # 'mat_residual',
            "mat_vecmul_iter",
            "tensor3_elemadd",
            "tensor3_ttm",
            "tensor3_ttv",
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
        glb_tests_fp = [
            "tests/fp_pointwise",
            "tests/fp_arith",
            "tests/fp_comp",
            "tests/fp_conv_7_7",
        ]
        resnet_tests = []
        resnet_tests_fp = []
        hardcoded_dense_tests = [
            "apps/depthwise_conv"
        ]
    elif args.config == "daily":
        width, height = 32, 16
        sparse_tests = [
            "vec_elemadd",
            "vec_elemmul",
            "vec_identity",
            "vec_scalar_mul",
            "mat_vecmul_ij",
            "mat_elemadd",
            "mat_elemadd_relu",
            "mat_elemadd_leakyrelu_exp",
            "mat_elemadd3",
            "mat_elemmul",
            "mat_identity",
            "mat_mattransmul",
            "matmul_ijk",
            "matmul_ijk_crddrop",
            "matmul_ijk_crddrop_relu",
            "matmul_ikj",
            "matmul_jik",
            "spmm_ijk_crddrop_fp",
            "spmm_ijk_crddrop",
            "spmm_ijk_crddrop_relu",
            "spmv",
            "spmv_relu",
            "masked_broadcast",
            "trans_masked_broadcast",
            # Turned off until SUB ordering fixed in mapping
            # 'mat_residual',
            "mat_sddmm",
            "mat_mask_tri",
            "mat_vecmul_iter",
            "tensor3_elemadd",
            "tensor3_elemmul",
            "tensor3_identity",
            "tensor3_innerprod",
            "tensor3_mttkrp",
            "tensor3_ttm",
            "tensor3_ttv",
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
        glb_tests_fp = [
            "tests/fp_pointwise",
            "tests/fp_arith",
            "tests/fp_conv_7_7",
            "apps/maxpooling_fp",
            "apps/matrix_multiplication_fp",
        ]
        resnet_tests = [
            "conv1",
            "conv4_1",
            "conv4_x",
            "conv5_x",  
            "conv2_x_residual",
            "conv5_x_residual",
        ]
        resnet_tests_fp = [
            "conv2_x_fp",
        ]
        hardcoded_dense_tests = [
            "apps/depthwise_conv"
        ]
    elif args.config == "full":
        width, height = 32, 16
        sparse_tests = [
            "vec_elemadd",
            "vec_elemmul",
            "vec_identity",
            "vec_scalar_mul",
            "mat_vecmul_ij",
            "mat_elemadd",
            "mat_elemadd_relu",
            "mat_elemadd_leakyrelu_exp",
            "mat_elemadd3",
            "mat_elemmul",
            "mat_identity",
            "mat_mattransmul",
            "matmul_ijk",
            "matmul_ijk_crddrop",
            "matmul_ijk_crddrop_relu",
            "matmul_ikj",
            "matmul_jik",
            "spmm_ijk_crddrop",
            "spmm_ijk_crddrop_relu",
            "spmv",
            "spmv_relu",
            "masked_broadcast",
            "trans_masked_broadcast",
            # Turned off until SUB ordering fixed in mapping
            # 'mat_residual',
            "mat_sddmm",
            "mat_mask_tri",
            "mat_vecmul_iter",
            "tensor3_elemadd",
            "tensor3_elemmul",
            "tensor3_identity",
            "tensor3_innerprod",
            "tensor3_mttkrp",
            "tensor3_mttkrp_unfused1",
            "tensor3_mttkrp_unfused2",
            "tensor3_ttm",
            "tensor3_ttv",

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
        glb_tests_fp = [
            "tests/fp_pointwise",
            "tests/fp_arith",
            "tests/fp_comp",
            "tests/fp_conv_7_7",
            "apps/maxpooling_fp",
            "apps/matrix_multiplication_fp",
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
            "conv2_x_residual",
            "conv5_x_residual",
        ]
        resnet_tests_fp = [
            "conv2_x_fp"
        ]
        hardcoded_dense_tests = [
            "apps/depthwise_conv"
        ]
    elif args.config == "resnet":
        width, height = 32, 16
        sparse_tests = []
        glb_tests = []
        glb_tests_fp = []
        resnet_tests = [
            "conv1",
            "conv2_x",
            "conv3_1",
            "conv3_x",
            "conv4_1",
            "conv4_x",
            "conv5_1",
            "conv5_x",
            "conv2_x_residual",
            "conv3_x_residual",
            "conv4_x_residual",
            "conv5_x_residual",
        ]
        resnet_tests_fp = []
        hardcoded_dense_tests = []

    else:
        raise NotImplementedError(f"Unknown test config: {args.config}")

    print(f"--- Running regression: {args.config}")
    info = []
    t = gen_garnet(width, height)
    info.append(["garnet", t])

    generate_sparse_bitstreams(sparse_tests, width, height)

    for test in sparse_tests:
        t0, t1, t2 = test_sparse_app(test)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in glb_tests:
        t0, t1, t2 = test_dense_app(test, 
                                    width, height, args.env_parameters, extra_args)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in glb_tests_fp:
        t0, t1, t2 = test_dense_app(test, 
                                    width, height, args.env_parameters, extra_args, use_fp=True)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in resnet_tests:
        if "residual" in test:
            t0, t1, t2 = test_dense_app("apps/resnet_residual",
                                        width, height, args.env_parameters, extra_args, layer=test)
            info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
        else:
            t0, t1, t2 = test_dense_app("apps/resnet_output_stationary",
                                        width, height, args.env_parameters, extra_args, layer=test)
            info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in resnet_tests_fp:
        if "residual" in test:
            t0, t1, t2 = test_dense_app("apps/conv2D_residual_fp",
                                        width, height, args.env_parameters, extra_args, layer=test, use_fp=True)
            info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
        else:
            t0, t1, t2 = test_dense_app("apps/conv2D_fp",
                                        width, height, args.env_parameters, extra_args, layer=test, use_fp=True)
            info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in hardcoded_dense_tests:
        t0, t1, t2 = test_hardcoded_dense_app(test,
                                    width, height, args.env_parameters, extra_args)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
        
    print(tabulate(info, headers=["step", "total", "compile", "map", "test"]))


def gather_tests(tags):
    pass
