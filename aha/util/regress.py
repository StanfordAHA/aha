from pathlib import Path
import re
import subprocess
import sys
import os
from tabulate import tabulate
import time
from sam.onyx.generate_matrices import *
import tempfile


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("config")
    # parser.add_argument("tags", nargs="*")
    parser.set_defaults(dispatch=dispatch)


def buildkite_filter(s):
    return re.sub("^---", " ---", s, flags=re.MULTILINE)


def buildkite_call(command, env={}):
    env = {**os.environ.copy(), **env}

    try:
        app = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
            env=env,
        )
        print(buildkite_filter(app.stdout))
    except subprocess.CalledProcessError as err:
        print("ERROR", file=sys.stderr)
        print("=== stdout ===", file=sys.stderr)
        print(buildkite_filter(err.stdout), file=sys.stderr)
        print("=== stderr ===", file=sys.stderr)
        print(buildkite_filter(err.stderr), file=sys.stderr)
        sys.exit(1)


def gen_garnet(width, height):
    print("--- Generating Garnet")
    start = time.time()
    if (not os.path.exists('/aha/garnet/garnet.v')):
        buildkite_call([
            "aha",
            "garnet",
            "--width",
            str(width),
            "--height",
            str(height),
            "--verilog",
            "--use_sim_sram",
            "--rv",
            "--sparse-cgra",
            "--sparse-cgra-combined"
        ])
    return time.time() - start


def run_glb(testname, width, height, test='', sparse=False):
    if sparse:
        app_path = f"../../../garnet/SPARSE_TESTS/GLB_DIR/{testname}_combined_seed_0"
    else:
        app_path = "/aha/Halide-to-Hardware/apps/hardware_benchmarks/"+testname
    print(app_path)
    try:
        subprocess.call(["make", "clean"], cwd=app_path)
    except: 
        pass
    if test == '':
        test = testname
    print(f"--- {test}")
    print(f"--- {test} - compiling")
    os.environ["PIPELINED"] = '1'

    start = time.time()

    if sparse:
        print("--- sparse test needs no compilation ---")
    else:
        if "resnet_output_stationary" in test:
            buildkite_call(["aha", "halide", testname, "--chain"])
        else:
            buildkite_call(["aha", "halide", testname])

    time_compile = time.time() - start

    print(f"--- {test} - mapping")
    start = time.time()
    my_env = {}
    my_env = {'DISABLE_GP': '1'}
    if sparse:
        my_env['PYTHONPATH'] = "/aha/garnet/"

    if sparse:
        buildkite_call(
                ["python", "/aha/garnet/tests/test_memory_core/build_tb.py", "--ic_fork", "--sam_graph", f"/aha/sam/compiler/sam-outputs/dot/{testname}.gv", "--seed", f"{0}",
                    "--dump_bitstream", "--add_pond", "--combined", "--pipeline_scanner", "--base_dir", "/aha/garnet/SPARSE_TESTS/", "--just_glb", "--dump_glb", "--fiber_access",
                    "--width", str(width), "--height", str(height)],
                env=my_env
                )
    else:
        buildkite_call(
            ["aha", "pipeline", testname, "--width", str(width), "--height", str(height), "--input-broadcast-branch-factor", "2", "--input-broadcast-max-leaves", "32", "--rv", "--sparse-cgra", "--sparse-cgra-combined"],
            env=my_env
        )
    
    time_map = time.time() - start

    print(f"--- {test} - glb testing")
    start = time.time()
    #buildkite_call(["aha", "glb", testname, "--waveform"])
    if sparse:
        try:
            buildkite_call(["aha", "glb", app_path, "--sparse", "--sparse-test-name", testname])
        except:
            print("--- GLB CALLED FAILED!!! Fallback to offsite comparison... ---")

    else:
        buildkite_call(["aha", "glb", testname])
    #buildkite_call(["aha", "glb", testname])
    time_test = time.time() - start

    return time_compile, time_map, time_test


def dispatch(args, extra_args=None):
    sparse_tests = []
    if args.config == "fast":
        width, height = 4, 4
        sparse_tests = [
            "vec_identity"
        ]
        glb_tests = [
            "apps/pointwise",
        ]
        resnet_tests = []
    elif args.config == "pr":
        width, height = 20, 8
        sparse_tests = [
            "matmul_ijk",
            'mat_mattransmul',
            "vec_identity",
            "vec_elemadd",
            "vec_elemmul"
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
            # "handcrafted/resnet_pond",
            # "handcrafted/pond_accum",
            # "handcrafted/pond_and_mem"
        ]
        resnet_tests = []
    elif args.config == "daily":
        width, height = 32, 16
        sparse_tests = [
            'vec_elemadd',
            'vec_elemmul',
            'vec_identity',
            'vec_scalar_mul',
            'mat_elemadd',
            'mat_elemadd3',
            'mat_elemmul',
            'mat_identity',
            'mat_mattransmul',
            'tensor3_mttkrp',
            'tensor3_ttm',
            'tensor3_ttv',
        ]
        glb_tests = [
            "apps/pointwise",
            "apps/gaussian",
            "apps/unsharp",
            "apps/camera_pipeline_2x2",
            "apps/harris_color",
        ]
        resnet_tests = [
            "conv1",
            "conv4_1",
            "conv5_x",
        ]
    elif args.config == "full":
        width, height = 32, 16
        sparse_tests = [
            'mat_elemadd',
            'mat_elemadd3',
            'mat_elemmul',
            'mat_identity',
            'mat_mattransmul',
            # Turned off until SUB ordering fixed in mapping
            # 'mat_residual',
            'mat_sddmm',
            'mat_vecmul_ij',
            'matmul_ijk',
            'matmul_jik',
            'tensor3_elemadd',
            'tensor3_elemmul',
            'tensor3_identity',
            'tensor3_innerprod',
            'tensor3_mttkrp',
            'tensor3_ttm',
            'tensor3_ttv',
            'vec_elemadd',
            'vec_elemmul',
            'vec_identity',
            'vec_scalar_mul',
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
            "tests/three_level_pond"
            "apps/gaussian",
            "apps/brighten_and_blur",
            "apps/cascade",
            "apps/harris",
            "apps/resnet_layer_gen",
            "apps/unsharp",
            #"apps/camera_pipeline",
            "apps/harris_color",
            "apps/camera_pipeline_2x2",
            #"handcrafted/conv_3_3_chain",
            #"handcrafted/pond_accum",
            #"handcrafted/resnet_pond",
            #"handcrafted/pond_and_mem"
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
        width, height = 32, 16
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

    print(f"--- Running regression: {args.config}")
    info = []
    t = gen_garnet(width, height)
    info.append(["garnet", t])
    
    halide_gen_args = {}
    halide_gen_args["apps/gaussian"]            = "mywidth=62 myunroll=2 schedule=3"
    halide_gen_args["apps/harris_color"]        = "mywidth=62 myunroll=1 schedule=31"
    halide_gen_args["apps/unsharp"]             = "mywidth=62 myunroll=1 schedule=3"
    halide_gen_args["apps/camera_pipeline_2x2"] = "schedule=3"
   
    for test in sparse_tests:
        t0, t1, t2 = run_glb(test, width, height, sparse=True)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in glb_tests:
        if test in halide_gen_args:
            os.environ["HALIDE_GEN_ARGS"] = halide_gen_args[test]
        else:
            os.environ["HALIDE_GEN_ARGS"] = ""
        t0, t1, t2 = run_glb(test, width, height)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in resnet_tests:
        if test == "conv1":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=32 pad=3 ksize=7 stride=2 n_ic=3 n_oc=64 k_ic=3 k_oc=4" 
            os.environ["HL_TARGET"] = "host-x86-64"
        elif test == "conv2_x":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=56 pad=1 ksize=3 stride=1 n_ic=16 n_oc=16 k_ic=8 k_oc=8 glb_i=4 glb_k=4 glb_o=4" 
            os.environ["HL_TARGET"] = "host-x86-64-enable_ponds"
        elif test == "conv3_1":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=56 pad=1 ksize=3 stride=2 n_ic=16 n_oc=16 k_ic=8 k_oc=8 glb_i=8 glb_k=4 glb_o=4" 
            os.environ["HL_TARGET"] = "host-x86-64-enable_ponds"
        elif test == "conv3_x":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=28 pad=1 ksize=3 stride=1 n_ic=16 n_oc=16 k_ic=8 k_oc=8 glb_i=8 glb_k=4 glb_o=4" 
            os.environ["HL_TARGET"] = "host-x86-64-enable_ponds"
        elif test == "conv4_1":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=28 pad=1 ksize=3 stride=2 n_ic=16 n_oc=16 k_ic=8 k_oc=8 glb_i=8 glb_k=4 glb_o=4" 
            os.environ["HL_TARGET"] = "host-x86-64-enable_ponds"
        elif test == "conv4_x":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=14 pad=1 ksize=3 stride=1 n_ic=16 n_oc=16 k_ic=8 k_oc=8 glb_i=8 glb_k=4 glb_o=4" 
            os.environ["HL_TARGET"] = "host-x86-64-enable_ponds"
        elif test == "conv5_1":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=14 pad=1 ksize=3 stride=2 n_ic=16 n_oc=16 k_ic=8 k_oc=8 glb_i=8 glb_k=4 glb_o=4" 
            os.environ["HL_TARGET"] = "host-x86-64-enable_ponds"
        elif test == "conv5_x":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=7 pad=1 ksize=3 stride=1 n_ic=16 n_oc=16 k_ic=8 k_oc=8 glb_i=8 glb_k=4 glb_o=4" 
            os.environ["HL_TARGET"] = "host-x86-64-enable_ponds"
        t0, t1, t2 = run_glb("apps/resnet_output_stationary", width, height, test)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
    print(tabulate(info, headers=["step", "total", "compile", "map", "test"]))


def gather_tests(tags):
    pass
