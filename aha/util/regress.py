from pathlib import Path
import subprocess
import sys
from tabulate import tabulate
import time


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("config")
    # parser.add_argument("tags", nargs="*")
    parser.set_defaults(dispatch=dispatch)


def gen_garnet(width, height):
    print("--- Generating Garnet")
    start = time.time()
    subprocess.check_output(
        [
            "aha",
            "garnet",
            "--width",
            str(width),
            "--height",
            str(height),
            "--verilog",
            "--interconnect-only",
        ]
    )
    return time.time() - start


def run_test(testname, width, height):
    print(f"--- {testname}")
    print(f"--- {testname} - compiling")
    start = time.time()
    subprocess.check_output(["aha", "halide", testname])
    time_compile = time.time() - start

    print(f"--- {testname} - mapping")
    start = time.time()
    subprocess.check_output(
        ["aha", "map", testname, "--width", str(width), "--height", str(height)]
    )
    time_map = time.time() - start

    print(f"--- {testname} - testing")
    start = time.time()
    subprocess.check_output(["aha", "test", testname])
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
        ]
    elif args.config == "daily":
        width, height = 16, 16
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
        ]
    else:
        raise NotImplementedError(f"Unknown test config: {config}")

    info = []
    t = gen_garnet(width, height)
    info.append("garnet", t)
    for test in tests:
        t0, t1, t2 = run_test(test, width, height)
        info.append(test, t0 + t1 + t2, t0, t1, t2)
        print(tabulate(info, headers=["step", "total", "compile", "map", "test"]))


def gather_tests(tags):
    pass
