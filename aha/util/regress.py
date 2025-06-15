from pathlib import Path
import re
import json
import subprocess
import sys
import os
from tabulate import tabulate
import time
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


def buildkite_call(command, env={}, return_output=False, out_file=None):
    env = {**os.environ.copy(), **env}
    if return_output:
        app = subprocess.run(
            command,
            check=True,
            text=True,
            env=env,
            stdout=out_file,
        )
    else: 
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

        # Daemon is no good if/when we build new/different verilog
        buildkite_call("aha garnet --daemon kill".split())
        
        # No garnet verilog yet, so build it now.
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


def generate_sparse_bitstreams(sparse_tests, width, height, seed_flow, suitesparse_data_tile_pairs):
    if len(sparse_tests) == 0:
        return 0
    
    print(f"--- mapping all tests", flush=True)
    start = time.time()
    env_vars = {"PYTHONPATH": "/aha/garnet/", "EXHAUSTIVE_PIPE":"1"}
    start = time.time()
    all_sam_graphs = [f"/aha/sam/compiler/sam-outputs/onyx-dot/{testname}.gv" for testname in sparse_tests]

    if(seed_flow):
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
                "--width", str(width),
                "--height", str(height),
            ],
            env=env_vars,
        )
    else: 
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
                "--give_tensor",
                "--tensor_locs",
                "/aha/garnet/SPARSE_TESTS/MAT_TMP_DIR",
                "--width", str(width),
                "--height", str(height),
                "--suitesparse_data_tile_pairs", *suitesparse_data_tile_pairs,
            ],
            env=env_vars,
        )
    time_map = time.time() - start
    return time_map


def test_sparse_app(testname, seed_flow, suitesparse_data_tile_pairs, test=""):
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

    print(f"--- {test} - glb testing")
    if(seed_flow):
        print("RUNNING SEED FLOW", flush=True)
        start = time.time()
        buildkite_call(
            ["aha", "test", app_path, "--sparse", "--sparse-test-name", testname], env=env_vars,
        )
        time_test = time.time() - start
    else:
        print("RUNNING SS FLOW", flush=True)
        start = time.time()
        dataset_runtime_dict = defaultdict(float)
        for ss_tile_pair in suitesparse_data_tile_pairs:
            ss_tile_pair = ss_tile_pair.split("MAT_TMP_DIR/")[1]
            ss_tile_pair_sparse_testname = ss_tile_pair.split("-")[0]
            if ss_tile_pair_sparse_testname != testname:
                continue
            with open("/aha/garnet/aha_test_out.txt", 'w') as test_out_file:
                buildkite_call(
                    ["aha", 
                    "test", 
                    f"../../../garnet/SPARSE_TESTS/{test}_{ss_tile_pair}/GLB_DIR/{test}_combined_seed_{ss_tile_pair}",  
                    "--sparse", 
                    "--sparse-test-name", 
                    f"{test}", 
                    "--sparse-comparison", 
                    f"/aha/garnet/SPARSE_TESTS/{test}_{ss_tile_pair}/GLB_DIR/{test}_combined_seed_{ss_tile_pair}/"
                    ], env=env_vars,
                    return_output=True,
                    out_file = test_out_file
                )
            command = "grep \"total time\" /aha/garnet/aha_test_out.txt"
            result = subprocess.check_output(command, shell=True, encoding='utf-8')
            total_time_line = result.split("\n")[0]
            time_str = total_time_line.split(" ns")[0].split(" ")[-1]
            time_value = float(time_str)
            split_str = f"{testname}-"
            dataset = total_time_line.split(split_str)[1].split("_")[0]
            dataset_runtime_dict[dataset] += time_value

        with open("/aha/garnet/suitesparse_perf_out.txt", 'a') as perf_out_file:
            for dataset, time_value in dataset_runtime_dict.items():
                perf_out_file.write(f"{testname}        {dataset}        {time_value}\n")    


        time_test = time.time() - start
    return 0, 0, time_test


def test_dense_app(test, width, height, env_parameters, extra_args, layer=None, use_fp=False):
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

    buildkite_call(
        [
            "aha",
            "pnr",
            test,
            "--width", str(width),
            "--height", str(height),
            "--env-parameters", env_parameters,
        ] + use_daemon + layer_array
    )
    time_map = time.time() - start

    print(f"--- {testname} - glb testing", flush=True)
    start = time.time()
    if use_fp:
        buildkite_call(["aha", "test", test, "--dense-fp"])
    else:
        buildkite_call(["aha", "test", test])
    time_test = time.time() - start

    return time_compile, time_map, time_test


def test_hardcoded_dense_app(test, width, height, env_parameters, extra_args, layer=None,):
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

    buildkite_call(
        [
            "aha",
            "pnr",
            test,
            "--width", str(width),
            "--height", str(height),
            "--generate-bitstream-only",
            "--env-parameters", env_parameters,
        ] + use_daemon + layer_array
    )
    time_map = time.time() - start

    print(f"--- {testname} - glb testing", flush=True)
    start = time.time()
    buildkite_call(["aha", "test", test])
    time_test = time.time() - start

    return time_compile, time_map, time_test


def dispatch(args, extra_args=None):
    seed_flow = True
    # suitesparse_data = ["bcsstm26"]
    suitesparse_data = ["rand_large_tensor5"]
    if args.config == "fast":
        width, height = 28, 16
        # first use 28x16 to generate rtl
        # to unroll, use 12x16 to generate bitstream
        sparse_tests = [
            # sparse matrix expressions
            # "mat_elemadd3",
            # "mat_elemmul", # unrolled
            # "mat_vecmul_ij", # have to use different cgra size unrolling (10x16)
            # "matmul_ikj", # unrolled
            # "matmul_ijk_crddrop", # unrolled
            # sparse ternsor expressions
            # "tensor3_ttv", #unrolled
            # "tensor3_ttm", # have to use different cgra size (e.g. 20x16)
            # "tensor3_innerprod",
            # "tensor3_mttkrp"
            # sparse-ml kernels
            # "fp_matmul_ikj", # unrolled
            # "fp_relu_matmul_ikj", # unrolled
            # "fp_relu_matmul_ijk_crddrop", # unrolled
            # "fp_relu_spmm_ikj", # unrolled
            # "fp_relu_spmm_ijk_crddrop", # unrolled
            # "fp_spmm_ikj", # unrolled
            # "fp_matmul_ijk_crddrop", # unrolled
            # "fp_spmm_ijk_crddrop", # unrolled
            # "mat_dn2sp", # have to use different cgra size unrolling (10x16)
            # "fp_mat_elemadd_relu", # unrolled
            # "fp_mat_elemadd", # unrolled
            # "fp_dense_mat_elemadd_relu" # unrolled
            # sparse ml micro-benchmarks
            # "fp_spmm_ijk_crddrop_relu",
            # "fp_spmm_ijk_crddrop_elu",
            # "mat_elemadd_leakyrelu_exp",
            # "fp_mat_elemadd",
            # "fp_spmm_ijk",
        ]
        glb_tests = [
            # "apps/gaussian",
            # "apps/unsharp",
            # "apps/harris_color",
            # "apps/camera_pipeline_2x2"
        ]
        resnet_tests = [
            # "conv1",
            # "conv2_x",
            # "conv3_1",
            # "conv3_x",
            # "conv4_1",
            # "conv4_x",
            # "conv5_1",
            # "conv5_x"
        ]
        glb_tests_fp = [
            # "apps/matrix_multiplication_fp",
            # "apps/relu_layer_fp",
            # "apss/relu_layer3_fp",
        ]
        hardcoded_dense_tests = []
    elif args.config == "pr":
        width, height = 28, 16
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
        glb_tests = []
        resnet_tests = []
        hardcoded_dense_tests = [
            "apps/depthwise_conv"
        ]
    elif args.config == "daily":
        width, height = 28, 16
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
        resnet_tests = [
            "conv1",
            "conv4_1",
            "conv4_x",
            "conv5_x",
        ]
        hardcoded_dense_tests = [
            "apps/depthwise_conv"
        ]
    elif args.config == "full":
        width, height = 28, 16
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
        hardcoded_dense_tests = [
            "apps/depthwise_conv"
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
        hardcoded_dense_tests = []

    else:
        raise NotImplementedError(f"Unknown test config: {args.config}")


    print(f"--- Running regression: {args.config}", flush=True)
    info = []
    t = gen_garnet(width, height)
    info.append(["garnet", t])

    suitesparse_data_tile_pairs = []

    if not(seed_flow):
        if not os.path.exists("/aha/garnet/SPARSE_TESTS/MAT_TMP_DIR"):
            os.mkdir("/aha/garnet/SPARSE_TESTS/MAT_TMP_DIR")

        # Remove whatever is in MAT_TMP_DIR first
        exit_status = os.system(f"rm -rf /aha/garnet/SPARSE_TESTS/MAT_TMP_DIR/*")
        if os.WEXITSTATUS(exit_status) != 0:
            raise RuntimeError(f"Command 'rm -rf /aha/garnet/SPARSE_TESTS//MAT_TMP_DIR/*' returned non-zero exit status {os.WEXITSTATUS(exit_status)}.")
        
        for test in sparse_tests:
            for suitesparse_datum in suitesparse_data:
                if "tensor" not in test:
                    command = "python3 /aha/garnet/copy_formatted.py " + test + " " + suitesparse_datum
                else:
                    command = "python3 /aha/garnet/copy_formatted_tensor_tiling.py " + test + " " + suitesparse_datum
                subprocess.call(command, shell=True)
            this_sparse_test_tile_pairs = glob.glob(f"/aha/garnet/SPARSE_TESTS/MAT_TMP_DIR/{test}*")
            suitesparse_data_tile_pairs.extend(this_sparse_test_tile_pairs)

    #if not(seed_flow):
    #    suitesparse_data_tile_pairs = os.listdir("/aha/garnet/SPARSE_TESTS/MAT_TMP_DIR")

    print("HERE ARE THE SS DATA TILE PAIRS!")
    print(suitesparse_data_tile_pairs)

    generate_sparse_bitstreams(sparse_tests, width, height, seed_flow, suitesparse_data_tile_pairs)

    if not(seed_flow):
        if os.path.exists("/aha/garnet/suitesparse_perf_out.txt"):
            os.system("rm /aha/garnet/suitesparse_perf_out.txt")
        with open("/aha/garnet/suitesparse_perf_out.txt", 'w') as perf_out_file:
            perf_out_file.write("SPARSE TEST        SS DATASET        TOTAL RUNTIME (ns)\n\n")

    for test in sparse_tests:
        t0, t1, t2 = test_sparse_app(test, seed_flow, suitesparse_data_tile_pairs)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in glb_tests:
        t0, t1, t2 = test_dense_app(test, 
                                    width, height, args.env_parameters, extra_args)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in resnet_tests:
        t0, t1, t2 = test_dense_app("apps/resnet_output_stationary",
                                    width, height, args.env_parameters, extra_args, layer=test)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in hardcoded_dense_tests:
        t0, t1, t2 = test_hardcoded_dense_app(test,
                                    width, height, args.env_parameters, extra_args)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
    
    for test in glb_tests_fp:
        t0, t1, t2 = test_dense_app(test, 
                                    width, height, args.env_parameters, extra_args, use_fp=True)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
        
    print(f"+++ TIMING INFO", flush=True)
    print(tabulate(info, headers=["step", "total", "compile", "map", "test"]), flush=True)


def gather_tests(tags):
    pass
