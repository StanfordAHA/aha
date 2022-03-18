from pathlib import Path
import re
import subprocess
import sys
import os
from tabulate import tabulate
import time


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
    buildkite_call([
        "aha",
        "garnet",
        "--width",
        str(width),
        "--height",
        str(height),
        "--verilog"
        #"--interconnect-only"
    ])
    return time.time() - start


def run_test(testname, width, height):
    print(f"--- {testname}")
    print(f"--- {testname} - compiling")
    start = time.time()
    buildkite_call(["aha", "halide", testname])
    time_compile = time.time() - start

    print(f"--- {testname} - mapping")
    os.environ["PIPELINED"] = '1'
    start = time.time()
    buildkite_call(
        ["aha", "pipeline", testname, "--width", str(width), "--height", str(height)]
    )
    time_map = time.time() - start

    print(f"--- {testname} - testing")
    start = time.time()
    buildkite_call(["aha", "test", testname])
    time_test = time.time() - start

    return time_compile, time_map, time_test


def run_glb(testname, width, height, test=''):
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
    buildkite_call(["aha", "halide", testname])
    time_compile = time.time() - start

    print(f"--- {test} - mapping")
    start = time.time()
    my_env = {}
    #if testname == "apps/unsharp" or testname == "apps/camera_pipeline":
    my_env = {'DISABLE_GP': '1'}
    buildkite_call(
        ["aha", "pipeline", testname, "--width", str(width), "--height", str(height)],
        env=my_env
    )
    time_map = time.time() - start

    print(f"--- {test} - glb testing")
    start = time.time()
    buildkite_call(["aha", "glb", testname])
    time_test = time.time() - start

    return time_compile, time_map, time_test


def dispatch(args, extra_args=None):
    if args.config == "fast":
        width, height = 4, 2
        glb_tests = [
            "apps/pointwise",
        ]
        tests = []
        resnet_tests = []
    elif args.config == "pr":
        width, height = 8, 8
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
        tests = []
        resnet_tests = []
    elif args.config == "daily":
        width, height = 32, 16
        tests = [
            # "apps/pointwise",
            # "tests/rom",
            # "tests/ushift",
            # "tests/arith",
            # "tests/absolute",
            # "tests/scomp",
            # "tests/ucomp",
            # "tests/uminmax",
            # "tests/conv_1_2",
            # "tests/conv_2_1",
            # "tests/conv_3_3",
            # "apps/gaussian",
            # "apps/cascade",
            # "apps/harris",
            # "apps/resnet_layer_gen",
            # "handcrafted/conv_3_3_chain",
            # "handcrafted/pond_accum",
            # "handcrafted/resnet_pond",
            # "handcrafted/pond_and_mem",
        ]
        glb_tests = [
            "apps/gaussian",
            "apps/unsharp",
            "apps/resnet_layer_gen"
        ]
        resnet_tests = [
            "conv1",
            "conv3_x",
            "conv4_1",
        ]
    elif args.config == "full":
        width, height = 32, 16
        tests = []
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
            "apps/camera_pipeline"
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
        tests = []
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
        raise NotImplementedError(f"Unknown test config: {config}")

    print(f"--- Running regression: {args.config}")
    info = []
    t = gen_garnet(width, height)
    info.append(["garnet", t])
    
    halide_gen_args = {}
    halide_gen_args["apps/gaussian"] = "mywidth=184 myunroll=8 schedule=3"

    for test in tests:
        if test in halide_gen_args:
            os.environ["HALIDE_GEN_ARGS"] = halide_gen_args[test]
        else:
            os.environ["HALIDE_GEN_ARGS"] = ""
        t0, t1, t2 = run_test(test, width, height)
        info.append([test, t0 + t1 + t2, t0, t1, t2])
        print(tabulate(info, headers=["step", "total", "compile", "map", "test"]))
    for test in glb_tests:
        if test in halide_gen_args:
            os.environ["HALIDE_GEN_ARGS"] = halide_gen_args[test]
        else:
            os.environ["HALIDE_GEN_ARGS"] = ""
        t0, t1, t2 = run_glb(test, width, height)
    for test in resnet_tests:
        if test == "conv1":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=32 pad=3 ksize=7 stride=2 n_ic=3 n_oc=64 k_ic=3 k_oc=16" 
        elif test == "conv2_x":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=56 pad=1 ksize=3 stride=1 n_ic=16 n_oc=16 k_ic=8 k_oc=8" 
        elif test == "conv3_1":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=56 pad=1 ksize=3 stride=2 n_ic=16 n_oc=16 k_ic=8 k_oc=8" 
        elif test == "conv3_x":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=28 pad=1 ksize=3 stride=1 n_ic=16 n_oc=16 k_ic=8 k_oc=8" 
        elif test == "conv4_1":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=28 pad=1 ksize=3 stride=2 n_ic=16 n_oc=16 k_ic=8 k_oc=8" 
        elif test == "conv4_x":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=14 pad=1 ksize=3 stride=1 n_ic=16 n_oc=16 k_ic=8 k_oc=8" 
        elif test == "conv5_1":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=14 pad=1 ksize=3 stride=2 n_ic=16 n_oc=16 k_ic=8 k_oc=8" 
        elif test == "conv5_x":
            os.environ["HALIDE_GEN_ARGS"] = "in_img=7 pad=1 ksize=3 stride=1 n_ic=16 n_oc=16 k_ic=8 k_oc=8" 
        t0, t1, t2 = run_glb("apps/resnet_output_stationary", width, height, test)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
        print(tabulate(info, headers=["step", "total", "compile", "map", "test"]))


def gather_tests(tags):
    pass
