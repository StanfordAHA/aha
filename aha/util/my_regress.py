from pathlib import Path
import re
import subprocess
import sys
from tabulate import tabulate
import time


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("config")
    parser.add_argument("--gen", action='store_true')
    # parser.add_argument("tags", nargs="*")
    parser.set_defaults(dispatch=dispatch)


def buildkite_filter(s):
    return re.sub("^---", " ---", s, flags=re.MULTILINE)


def buildkite_call(command):
    try:
        app = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
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
        "--verilog",
        "--interconnect-only"
    ])
    return time.time() - start


def run_test(testname, width, height):
    print(f"--- {testname}")
    print(f"--- {testname} - compiling")
    start = time.time()
    buildkite_call(["aha", "halide", testname])
    time_compile = time.time() - start

    print(f"--- {testname} - mapping")
    start = time.time()
    buildkite_call(
        ["aha", "map", testname, "--width", str(width), "--height", str(height)]
    )
    time_map = time.time() - start

    print(f"--- {testname} - testing")
    start = time.time()
    buildkite_call(["aha", "test", testname])
    time_test = time.time() - start

    return time_compile, time_map, time_test


def dispatch(args, extra_args=None):
    if args.config == "fast":
        width, height = 4, 2
        tests = [
            "apps/pointwise",
        ]
    elif args.config == "pr":
        width, height = 6, 6
        tests = [
            "tests/ushift",
            "tests/arith",
            "tests/absolute",
            "apps/pointwise",
            "tests/scomp",
            "tests/ucomp",
            "tests/uminmax",
            "tests/rom",
            "tests/conv_1_2",
            "tests/conv_2_1",
            "apps/resnet_pond"
        ]
    elif args.config == "daily":
        width, height = 16, 16
        tests = [
            "handcrafted/conv_3_3_chain",
            #"apps/resnet_layer_auto", #will not run
            "handcrafted/pond_accum", 
            "handcrafted/resnet_pond",
            "tests/conv_3_3",
            "apps/cascade",
            "tests/conv_1_2",
            "apps/harris",
            #"tests/rom",  #test did notmatch 
            "tests/ushift",
            "tests/arith", 
            "apps/pointwise",
            "apps/gaussian",
            #"apps/resnet_layer_gen", #halide image
            "tests/absolute",
            "tests/scomp",
            "tests/ucomp",
            "tests/uminmax",
            "tests/conv_2_1",
        ]
    elif args.config == "full":
        width, height = 32, 16
        tests = [
            "tests/ushift",
            "tests/arith",
            "tests/absolute",
            "apps/pointwise",
            "tests/scomp",
            "tests/ucomp",
            "tests/uminmax",
            "tests/rom",
            "tests/conv_1_2",
            "tests/conv_2_1",
            "apps/cascade",
            "apps/harris",
            "apps/gaussian",
            "tests/conv_3_3",
            "apps/resnet_layer_gen",
            "apps/resnet_pond"
        ]
    elif args.config == "jeff":
        width, height = 32, 16
        tests = [
            "tests/boolean_ops",
            ###"tests/bitwise", # problems with xor
            "tests/equal",
            "tests/ternary",
            "tests/sminmax",
            "tests/sshift",
            ###"tests/conv_5_5",         # KeyError: 'config_21_config_addr'
            ###"tests/inout_cgraconfig", # doesn't work
            ###"apps/unsharp",           # no divide
            "apps/brighten_and_blur"
            ###"apps/demosaic_complex",
            ###"apps/resnet",
            ###"apps/mobilenet",
        ]
    else:
        raise NotImplementedError(f"Unknown test config: {config}")

    print(f"--- Running regression: {args.config}")
    info = []
    if (args.gen):
        t = gen_garnet(width, height)
        info.append(["garnet", t])
    for test in tests:
        t0, t1, t2 = run_test(test, width, height)
        info.append([test, t0 + t1 + t2, t0, t1, t2])
        print(tabulate(info, headers=["step", "total", "compile", "map", "test"]))


def gather_tests(tags):
    pass

