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
    parser.add_argument("--include-dense-only-tests", action="store_true")
    parser.add_argument("--opal-workaround", action="store_true")
    parser.set_defaults(dispatch=dispatch)


def buildkite_filter(s):
    return re.sub("^---", " ---", s, flags=re.MULTILINE)


def buildkite_call(command, env={}, return_output=False, out_file=None):
    env = {**os.environ.copy(), **env}
    for retry in [1,2,3]:  # In case of SIGSEGV, retry up to three times
        try:
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
            break
        except subprocess.CalledProcessError as e:
            if 'SIGSEGV' in str(e):
                print(f'\n\n{e}\n')  # Print the error msg
                print(f'*** ERROR subprocess died {retry} time(s) with SIGSEGV')
                print('*** Will retry three times, then give up.\n\n')

                # if retry == 3: raise
                # - No! Don't raise the error! Higher-level aha.py has similar
                # - three-retry catchall, resulting in up to nine retries ! (Right?)
                # - Do this instead:
                if retry == 3:
                    assert False, 'ERROR: Three time loser'
            else:
                raise

def gen_garnet(width, height, dense_only=False):
    print("--- Generating Garnet", flush=True)
    start = time.time()
    if not os.path.exists("/aha/garnet/garnet.v"):
        # Daemon is no good if/when we build new/different verilog
        buildkite_call("aha garnet --daemon kill".split())
        
        # No garnet verilog yet, so build it now.

        buildkite_args = [
                            "aha",
                            "garnet",
                            "--width", str(width),
                            "--height", str(height),
                            "--verilog",
                            "--use_sim_sram",
                            "--glb_tile_mem_size", str(128),
                         ]

        if dense_only:
            buildkite_args.append("--dense-only")

        buildkite_call(buildkite_args)
        
    return time.time() - start


def generate_sparse_bitstreams(sparse_tests, width, height, seed_flow, suitesparse_data_tile_pairs, opal_workaround=False, unroll=1):
    if len(sparse_tests) == 0:
        return 0
    
    print(f"--- mapping all tests", flush=True)
    start = time.time()
    env_vars = {"PYTHONPATH": "/aha/garnet/", "EXHAUSTIVE_PIPE":"1"}
    # env_vars = {"PYTHONPATH": "/aha/garnet/"}
    start = time.time()
    all_sam_graphs = [f"/aha/sam/compiler/sam-outputs/onyx-dot/{testname}.gv" for testname in sparse_tests]

    if(seed_flow):
        build_tb_cmd = [
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
        ]
        if opal_workaround:
            build_tb_cmd.append("--opal-workaround")
        buildkite_call(
            build_tb_cmd,
            env=env_vars,
        )
    else: 
        build_tb_cmd = [
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
            "--unroll", str(unroll),
        ]
        if opal_workaround:
            build_tb_cmd.append("--opal-workaround")
        buildkite_call(
            build_tb_cmd,
            env=env_vars,
        )
    time_map = time.time() - start
    return time_map


def format_concat_tiles(test, suitesparse_data_tile_pairs, suitesparse_data, pipeline_num=64, unroll=1):
    script_path = "/aha/garnet/"
    pairs_cpy = suitesparse_data_tile_pairs.copy()
    all_tiles = []
    num_list = []
    for suitesparse_datum in suitesparse_data:
        pairs_cpy_tmp = pairs_cpy.copy()
        pairs_cpy = []
        test_l = []
        tile_format = ""
        for tile in pairs_cpy_tmp:
            if test in tile and suitesparse_datum in tile:
                test_l.append(int(tile.split("_")[-1][4:]))
                if tile_format == "":
                    tile_format = tile
            else:
                pairs_cpy.append(tile)
        test_l.sort()
        test_l = [str(x) for x in test_l]

        for i in range(0, len(test_l), pipeline_num):
            test_l_str = f"concat{i}"
            tile_format_t = tile_format.split("/")
            tile_format_name = tile_format_t[-1]
            tile_format_name = tile_format_name.split("_")
            tile_format_name[-1] = "tile_" + test_l_str
            tile_format_name = "_".join(tile_format_name)
            tile_format_t[-1] = tile_format_name
            tile_format_t = "/".join(tile_format_t)
            all_tiles.append(tile_format_t)

            if i + pipeline_num < len(test_l):
                test_l_s = test_l[i:i+pipeline_num]
            else:
                test_l_s = test_l[i:]
            true_pipeline_num = len(test_l_s)
            num_list.append(true_pipeline_num)
            print(f"CONCATENATING TILES {test_l_s}")
            subprocess.call(
                [
                    "python",
                    "/aha/garnet/concat_tiles.py",
                    test,
                    suitesparse_datum,
                    test_l_str,
                    str(unroll),
                    *test_l_s,
                ],
                cwd = script_path
            )
    return all_tiles, num_list


def test_sparse_app(testname, seed_flow, suitesparse_data_tile_pairs, pipeline_num_l=None, opal_workaround=False, test=""):
    if test == "":
        test = testname

    print(f"--- {test}")

    env_vars = {"PYTHONPATH": "/aha/garnet/"}

    app_path = f"{testname}_0/GLB_DIR/{testname}_combined_seed_0"
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
            ["aha", "test", app_path, "--sparse"], env=env_vars,
        )
        time_test = time.time() - start
    else:
        print("RUNNING SS FLOW", flush=True)
        use_pipeline = False
        print(suitesparse_data_tile_pairs)
        if pipeline_num_l is not None:
            assert len(pipeline_num_l) == len(suitesparse_data_tile_pairs), "Pipeline number list must be the same length as the number of tile pairs"
            use_pipeline = True
        else:
            use_pipeline = False
        start = time.time()
        dataset_runtime_dict = defaultdict(float)

        if use_pipeline:
            # Last batch won't have the same number of tiles as the rest, so we do two VCS calls
            suitesparse_data_tile_pairs = [ss_tile_pair.split("MAT_TMP_DIR/")[1] for ss_tile_pair in suitesparse_data_tile_pairs]
            suitesparse_data_tile_pairs = [f"{test}_{ss_tile_pair}/GLB_DIR/{test}_combined_seed_{ss_tile_pair}" for ss_tile_pair in suitesparse_data_tile_pairs]
            full_tile_pairs = suitesparse_data_tile_pairs[:-1]
            last_tile_pair = suitesparse_data_tile_pairs[-1]
            full_pipeline_num = pipeline_num_l[0]
            last_pipeline_num = pipeline_num_l[-1]
            full_pipeline_cmd = ["aha", "test"] + full_tile_pairs + ["--sparse", "--multiles", str(full_pipeline_num)]
            last_pipeline_cmd = ["aha", "test"] + [last_tile_pair] + ["--sparse", "--multiles", str(last_pipeline_num)]
            cmd_list = [full_pipeline_cmd, last_pipeline_cmd]
            if len(full_tile_pairs) == 0:
                cmd_list = [last_pipeline_cmd]
        else:
            suitesparse_data_tile_pairs = [ss_tile_pair.split("MAT_TMP_DIR/")[1] for ss_tile_pair in suitesparse_data_tile_pairs]
            suitesparse_data_tile_pairs = [f"{test}_{ss_tile_pair}/GLB_DIR/{test}_combined_seed_{ss_tile_pair}" for ss_tile_pair in suitesparse_data_tile_pairs]
            # split into batches of 64
            tile_pairs = [suitesparse_data_tile_pairs[i:i + 64] for i in range(0, len(suitesparse_data_tile_pairs), 64)]
            cmd_list = []
            # for each tile pair construct cmd
            for tile_pair in tile_pairs:
                cmd_list.append(["aha", "test"] + tile_pair + ["--sparse", "--multiles", str(1)])

        print(cmd_list)

        for cmd in cmd_list:
            buildkite_call(cmd, env=env_vars)
            command = "grep \"total time\" /aha/garnet/tests/test_app/run.log"
            results = subprocess.check_output(command, shell=True, encoding='utf-8')
            for result in results.split("\n"):
                if testname in result:
                    dataset_runtime_dict[result.split(f"{testname}-")[1].split("_")[0]] += float(result.split("\n")[0].split(" ns")[0].split(" ")[-1])

        with open("/aha/garnet/suitesparse_perf_out.txt", 'a') as perf_out_file:
            for dataset, time_value in dataset_runtime_dict.items():
                perf_out_file.write(f"{testname}        {dataset}        {time_value}\n")    


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
    seed_flow = True
    use_pipeline = False
    pipeline_num = 32
    unroll = 7
    suitesparse_data = ["qiulp"]

    # Preserve backward compatibility
    if args.config == "daily": args.config = "pr_aha"  # noqa
    if args.config == "pr": args.config = "pr_submod"  # noqa

    from aha.util.regress_tests.tests import Tests
    imported_tests = None

    # pr_aha1,2,3 are 4-hour, 3-hour, and 3-hour slices of pr_aha, respectively
    if args.config == "pr_aha1":
        imported_tests = Tests("pr_aha")
        imported_tests.resnet_tests.remove('conv2_x')  # This is actually *two* tests
        imported_tests.resnet_tests_fp.remove('conv2_x_fp')

    # NOTE conv2 breaks if don't do gaussian first(!) for details see issues:
    # https://github.com/StanfordAHA/garnet/issues/1070
    # https://github.com/StanfordAHA/aha/issues/1897
    elif args.config == "pr_aha2":
        imported_tests = Tests("BLANK")
        imported_tests.glb_tests = ["apps/gaussian"]
        # Note conv2 here is actually *two* tests, one sparse and one dense
        imported_tests.resnet_tests = [ 'conv2_x' ]

    elif args.config == "pr_aha3":
        imported_tests = Tests("BLANK")
        imported_tests.glb_tests = ["apps/gaussian"]
        imported_tests.resnet_tests_fp = [ 'conv2_x_fp' ]

    # For configs 'fast', 'pr_aha', 'pr_submod', 'full', 'resnet', see regress_tests/tests.py
    else:
        imported_tests = Tests(args.config)

    # Unpack imported_tests into convenient handles
    width, height = imported_tests.width, imported_tests.height
    sparse_tests = imported_tests.sparse_tests
    glb_tests = imported_tests.glb_tests
    glb_tests_fp = imported_tests.glb_tests_fp
    resnet_tests = imported_tests.resnet_tests
    resnet_tests_fp = imported_tests.resnet_tests_fp
    hardcoded_dense_tests = imported_tests.hardcoded_dense_tests

    print(f"--- Running regression: {args.config}", flush=True)
    info = []
    t = gen_garnet(width, height, dense_only=False)
    info.append(["garnet with sparse and dense", t])

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

    generate_sparse_bitstreams(sparse_tests, width, height, seed_flow, suitesparse_data_tile_pairs, opal_workaround=args.opal_workaround, unroll=unroll)

    if not(seed_flow):
        if os.path.exists("/aha/garnet/suitesparse_perf_out.txt"):
            os.system("rm /aha/garnet/suitesparse_perf_out.txt")
        with open("/aha/garnet/suitesparse_perf_out.txt", 'w') as perf_out_file:
            perf_out_file.write("SPARSE TEST        SS DATASET        TOTAL RUNTIME (ns)\n\n")

    for test in sparse_tests:
        if use_pipeline:
            assert (not seed_flow), "Pipeline mode is not supported with seed flow"
            tile_pairs, pipeline_num_l = format_concat_tiles(test, suitesparse_data_tile_pairs, suitesparse_data, pipeline_num, unroll)
            t0, t1, t2 = test_sparse_app(test, seed_flow, tile_pairs, pipeline_num_l, opal_workaround=args.opal_workaround)
            info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
        else:
            t0, t1, t2 = test_sparse_app(test, seed_flow, suitesparse_data_tile_pairs, opal_workaround=args.opal_workaround)
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

    if args.include_dense_only_tests:
        # DENSE ONLY TESTS
        # Remove sparse+dense garnet.v first 
        exit_status = os.system(f"rm /aha/garnet/garnet.v")
        if os.WEXITSTATUS(exit_status) != 0:
            raise RuntimeError(f"Command 'rm /aha/garnet/garnet.v' returned non-zero exit status {os.WEXITSTATUS(exit_status)}.")
        
        t = gen_garnet(width, height, dense_only=True)
        info.append(["garnet with dense only", t])

        num_dense_only_glb_tests = 5
        for test_index, test in enumerate(glb_tests):
            if test_index == num_dense_only_glb_tests:
                break
            t0, t1, t2 = test_dense_app(test, 
                                        width, height, args.env_parameters, extra_args, dense_only=True)
            info.append([test + "_glb dense only", t0 + t1 + t2, t0, t1, t2])

        for test in resnet_tests:
            # residual resnet test is not working with dense only mode
            if "residual" not in test:
                t0, t1, t2 = test_dense_app("apps/resnet_output_stationary",
                                            width, height, args.env_parameters, extra_args, layer=test)
                info.append([test + "_glb dense only", t0 + t1 + t2, t0, t1, t2])
 
    print(f"+++ TIMING INFO", flush=True)
    print(tabulate(info, headers=["step", "total", "compile", "map", "test"], floatfmt=".0f"), flush=True)


def gather_tests(tags):
    pass
