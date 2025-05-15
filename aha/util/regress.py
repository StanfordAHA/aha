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
import toml


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("config")
    parser.add_argument("--env-parameters", default="", type=str)
    parser.add_argument("--include-dense-only-tests", action="store_true")
    parser.add_argument("--include-no-zircon-tests", action="store_true")
    parser.add_argument("--opal-workaround", action="store_true")
    parser.add_argument("--non-seed-flow", action="store_true")
    parser.add_argument("--use-pipeline", action="store_true")
    parser.add_argument("--pipeline-num", default=32, type=int)
    parser.add_argument("--sparse-tile-pairs-list", default="", type=str, nargs="*")
    parser.add_argument("--unroll", default=1, type=int)
    parser.add_argument("--using-matrix-unit", action="store_true", default=True)
    parser.add_argument("--mu-datawidth", default=16, type=int)
    parser.add_argument("--no-zircon", action="store_true")
    parser.set_defaults(dispatch=dispatch)


def buildkite_filter(s):
    return re.sub("^---", " ---", s, flags=re.MULTILINE)


def buildkite_call(command, env={}, return_output=False, out_file=None):
    env = {**os.environ.copy(), **env}
    for retry in [1, 2, 3]:  # In case of SIGSEGV, retry up to three times
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


def gen_garnet(width, height, dense_only=False, using_matrix_unit=False, mu_datawidth=16, num_fabric_cols_removed=0, mu_oc_0=32):
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

        if using_matrix_unit:
            buildkite_args.append("--using-matrix-unit")
            buildkite_args.append("--mu-datawidth")
            buildkite_args.append(str(mu_datawidth))
            buildkite_args.append("--give-north-io-sbs")
            buildkite_args.append("--num-fabric-cols-removed")
            buildkite_args.append(str(num_fabric_cols_removed))
            buildkite_args.append("--mu-oc-0")
            buildkite_args.append(str(mu_oc_0))
            buildkite_args.append("--include-E64-hw")
            buildkite_args.append("--include-multi-bank-hw")
            buildkite_args.append("--include-mu-glb-hw")
            buildkite_args.append("--use-non-split-fifos")
            buildkite_args.append("--exclude-glb-ring-switch")

        buildkite_call(buildkite_args)

    return time.time() - start


def generate_sparse_bitstreams(sparse_tests, width, height, seed_flow, data_tile_pairs, kernel_name, opal_workaround=False, unroll=1, using_matrix_unit=False, num_fabric_cols_removed=0):
    if len(sparse_tests) == 0:
        return 0

    print(f"--- mapping all tests", flush=True)
    start = time.time()
    env_vars = {"PYTHONPATH": "/aha/garnet/", "EXHAUSTIVE_PIPE": "1"}
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
        if using_matrix_unit:
            build_tb_cmd.append("--using-matrix-unit")
            build_tb_cmd.append("--give-north-io-sbs")
            build_tb_cmd.append("--num-fabric-cols-removed")
            build_tb_cmd.append(str(num_fabric_cols_removed))
            build_tb_cmd.append("--include-E64-hw")
            build_tb_cmd.append("--use-non-split-fifos")
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
            "--kernel_name", kernel_name,
            "--data_tile_pairs", *data_tile_pairs,
            "--unroll", str(unroll),
        ]
        if opal_workaround:
            build_tb_cmd.append("--opal-workaround")
        if using_matrix_unit:
            build_tb_cmd.append("--using-matrix-unit")
            build_tb_cmd.append("--give-north-io-sbs")
            build_tb_cmd.append("--num-fabric-cols-removed")
            build_tb_cmd.append(str(num_fabric_cols_removed))
            build_tb_cmd.append("--include-E64-hw")
            build_tb_cmd.append("--use-non-split-fifos")
        buildkite_call(
            build_tb_cmd,
            env=env_vars,
        )
    time_map = time.time() - start
    return time_map


def format_concat_tiles(test, data_tile_pairs, kernel_name, pipeline_num=32, unroll=1):
    script_path = "/aha/garnet/"
    pairs_cpy = data_tile_pairs.copy()
    all_tiles = []
    num_list = []
    test_l = []
    tile_format = ""
    for tile in pairs_cpy:
        test_l.append(kernel_name + "-" + tile.replace("/", "_"))

    for i in range(0, len(test_l), pipeline_num):
        test_l_str = f"concat{i}"
        tile_format_t = f"{kernel_name}-tile_{test_l_str}"
        all_tiles.append(tile_format_t)

        if i + pipeline_num < len(test_l):
            test_l_s = test_l[i:i + pipeline_num]
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
                kernel_name,
                test_l_str,
                str(unroll),
                *test_l_s,
            ],
            cwd=script_path
        )

    return all_tiles, num_list


def test_sparse_app(testname, seed_flow, data_tile_pairs, pipeline_num_l=None, opal_workaround=False, test="", test_dataset_runtime_dict=None, using_matrix_unit=False, mu_datawidth=16, num_fabric_cols_removed=0, mu_oc_0=32):
    if test == "":
        test = testname

    print(f"--- {test}")

    env_vars = {"PYTHONPATH": "/aha/garnet/"}
    if using_matrix_unit:
        if num_fabric_cols_removed == 0:
            env_vars["WEST_IN_IO_SIDES"] = "1"
        env_vars["USING_MATRIX_UNIT"] = "1"
        env_vars["INCLUDE_MU_GLB_HW"] = "1"
        env_vars["MU_OC_0"] = str(mu_oc_0)
        env_vars["MU_DATAWIDTH"] = str(mu_datawidth)

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
        if pipeline_num_l is not None:
            assert len(pipeline_num_l) == len(data_tile_pairs), "Pipeline number list must be the same length as the number of tile pairs"
            use_pipeline = True
        else:
            use_pipeline = False
        start = time.time()
        if use_pipeline:
            data_tile_pairs = [f"{test}_{tile}/GLB_DIR/{test}_combined_seed_{tile}" for tile in data_tile_pairs]
            # Dictionary grouping tile pairs by pipeline number
            grouped_dict = defaultdict(list)
            for tile_pair, pipeline_num in zip(data_tile_pairs, pipeline_num_l):
                grouped_dict[pipeline_num].append(tile_pair)

            # create cmd_list for each pipeline number
            cmd_list = []
            for pipeline_num, tile_pairs in grouped_dict.items():
                # if list is longer than 64, split into batches of 64
                tile_pair_batches = [tile_pairs[i:i + 64] for i in range(0, len(tile_pairs), 64)]
                for tile_pair in tile_pair_batches:
                    cmd_list.append(["aha", "test"] + tile_pair + ["--sparse", "--multiles", str(pipeline_num)])

            if testname not in test_dataset_runtime_dict:
                test_dataset_runtime_dict[testname] = defaultdict(float)
        else:
            data_tile_pairs = [f"{test}_{tile}/GLB_DIR/{test}_combined_seed_{tile}" for tile in data_tile_pairs]
            # split into batches of 64
            tile_pairs = [data_tile_pairs[i:i + 64] for i in range(0, len(data_tile_pairs), 64)]
            cmd_list = []
            # for each tile pair construct cmd
            for tile_pair in tile_pairs:
                cmd_list.append(["aha", "test"] + tile_pair + ["--sparse", "--multiles", str(1)])
            if testname not in test_dataset_runtime_dict:
                test_dataset_runtime_dict[testname] = defaultdict(float)

        print(cmd_list)

        for cmd in cmd_list:
            if cmd is None:
                continue
            buildkite_call(cmd, env=env_vars)
            command = "grep \"total time\" /aha/garnet/tests/test_app/run.log"
            results = subprocess.check_output(command, shell=True, encoding='utf-8')
            for result in results.split("\n"):
                if testname in result:
                    test_dataset_runtime_dict[testname][result.split(f"{testname}_")[1].split("-")[0]] += float(result.split("\n")[0].split(" ns")[0].split(" ")[-1])

        time_test = time.time() - start
    return 0, 0, time_test


def test_dense_app(test, width, height, env_parameters, extra_args, layer=None, dense_only=False, use_fp=False, using_matrix_unit=False, mu_datawidth=16, num_fabric_cols_removed=0, mu_oc_0=32, dense_ready_valid=False, E64_mode_on=False, E64_multi_bank_mode_on=False):
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

    env_vars = {}
    if dense_ready_valid:
        env_vars["DENSE_READY_VALID"] = "1"
        env_vars["PIPELINED"] = "0"
        env_vars["MATCH_BRANCH_DELAY"] = "0"
        print(f"\033[92mINFO: Running {test} in dense ready-valid mode\033[0m")

    if E64_mode_on:
        env_vars["E64_MODE_ON"] = "1"
        print(f"\033[92mINFO: Running {test} with E64 MODE ON\033[0m")

    if E64_multi_bank_mode_on:
        print(f"\033[92mINFO: Running {test} with E64 MULTI BANK MODE ON\033[0m")
        env_vars["E64_MULTI_BANK_MODE_ON"] = "1"

    start = time.time()
    buildkite_call(["aha", "map", test, "--chain", "--env-parameters", env_parameters] + layer_array, env=env_vars)
    time_compile = time.time() - start
    breakpoint()

    print(f"--- {testname} - pnr and pipelining", flush=True)
    start = time.time()

    # To use daemon, call regress.py with args '--daemon auto'
    # --- extra_args=['--daemon', 'auto']
    use_daemon = []
    if (extra_args):
        if ('--daemon' in extra_args) and ('auto' in extra_args):
            use_daemon = ["--daemon", "auto"]

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

    env_vars = {}
    if dense_ready_valid:
        print(f"\033[92mINFO: Running {test} in dense ready-valid mode\033[0m")
        env_vars["DENSE_READY_VALID"] = "1"
        env_vars["EXHAUSTIVE_PIPE"] = "1"

    if E64_mode_on:
        print(f"\033[92mINFO: Running {test} with E64 MODE ON\033[0m")
        env_vars["E64_MODE_ON"] = "1"

    if E64_multi_bank_mode_on:
        print(f"\033[92mINFO: Running {test} with E64 MULTI BANK MODE ON\033[0m")
        env_vars["E64_MULTI_BANK_MODE_ON"] = "1"

    if using_matrix_unit:
        #TODO: Make these all env vars?
        buildkite_args.append("--using-matrix-unit")
        buildkite_args.append("--mu-datawidth")
        buildkite_args.append(str(mu_datawidth))
        buildkite_args.append("--give-north-io-sbs")
        buildkite_args.append("--num-fabric-cols-removed")
        buildkite_args.append(str(num_fabric_cols_removed))
        buildkite_args.append("--mu-oc-0")
        buildkite_args.append(str(mu_oc_0))
        buildkite_args.append("--include-E64-hw")
        buildkite_args.append("--include-multi-bank-hw")
        buildkite_args.append("--include-mu-glb-hw")
        buildkite_args.append("--use-non-split-fifos")

        env_vars["INCLUDE_E64_HW"] = "1"
        env_vars["INCLUDE_MULTI_BANK_HW"] = "1"

        if num_fabric_cols_removed == 0:
            env_vars["WEST_IN_IO_SIDES"] = "1"

        env_vars["USING_MATRIX_UNIT"] = "1"
        env_vars["INCLUDE_MU_GLB_HW"] = "1"
        env_vars["MU_OC_0"] = str(mu_oc_0)
        env_vars["MU_DATAWIDTH"] = str(mu_datawidth)
        env_vars["ADD_MU_INPUT_BUBBLES"] = "1"

    buildkite_call(buildkite_args, env=env_vars)
    time_map = time.time() - start

    print(f"--- {testname} - glb testing", flush=True)
    start = time.time()
    if use_fp:
        buildkite_call(["aha", "test", test, "--dense-fp"], env=env_vars)
    else:
        buildkite_call(["aha", "test", test], env=env_vars)
    time_test = time.time() - start

    return time_compile, time_map, time_test


def test_hardcoded_dense_app(test, width, height, env_parameters, extra_args, layer=None, dense_only=False, use_fp=False, using_matrix_unit=False, mu_datawidth=16, num_fabric_cols_removed=0, mu_oc_0=32, dense_ready_valid=False, E64_mode_on=False, E64_multi_bank_mode_on=False):
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
        raise RuntimeError(f"[ERROR] Please don't delete hardcoded bin folder")

    # To use daemon, call regress.py with args '--daemon auto'
    # --- extra_args=['--daemon', 'auto']
    use_daemon = []
    if (extra_args):
        if ('--daemon' in extra_args) and ('auto' in extra_args):
            use_daemon = ["--daemon", "auto"]

    print(f"--- {testname} - pnr and pipelining", flush=True)
    start = time.time()

    # To use daemon, call regress.py with args '--daemon auto'
    # --- extra_args=['--daemon', 'auto']
    use_daemon = []
    if (extra_args):
        if ('--daemon' in extra_args) and ('auto' in extra_args):
            use_daemon = ["--daemon", "auto"]

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

    env_vars = {}
    if dense_ready_valid:
        print(f"\033[92mINFO: Running {test} in dense ready-valid mode\033[0m")
        env_vars["DENSE_READY_VALID"] = "1"
        env_vars["EXHAUSTIVE_PIPE"] = "1"

    if E64_mode_on:
        print(f"\033[92mINFO: Running {test} with E64 MODE ON\033[0m")
        env_vars["E64_MODE_ON"] = "1"

    if E64_multi_bank_mode_on:
        print(f"\033[92mINFO: Running {test} with E64 MULTI BANK MODE ON\033[0m")
        env_vars["E64_MULTI_BANK_MODE_ON"] = "1"

    if using_matrix_unit:
        #TODO: Make these all env vars?
        buildkite_args.append("--using-matrix-unit")
        buildkite_args.append("--mu-datawidth")
        buildkite_args.append(str(mu_datawidth))
        buildkite_args.append("--give-north-io-sbs")
        buildkite_args.append("--num-fabric-cols-removed")
        buildkite_args.append(str(num_fabric_cols_removed))
        buildkite_args.append("--mu-oc-0")
        buildkite_args.append(str(mu_oc_0))
        buildkite_args.append("--include-E64-hw")
        buildkite_args.append("--include-multi-bank-hw")
        buildkite_args.append("--include-mu-glb-hw")
        buildkite_args.append("--use-non-split-fifos")

        env_vars["INCLUDE_E64_HW"] = "1"
        env_vars["INCLUDE_MULTI_BANK_HW"] = "1"

        if num_fabric_cols_removed == 0:
            env_vars["WEST_IN_IO_SIDES"] = "1"

        env_vars["USING_MATRIX_UNIT"] = "1"
        env_vars["INCLUDE_MU_GLB_HW"] = "1"
        env_vars["MU_OC_0"] = str(mu_oc_0)
        env_vars["MU_DATAWIDTH"] = str(mu_datawidth)
        env_vars["ADD_MU_INPUT_BUBBLES"] = "1"

    buildkite_call(buildkite_args, env=env_vars)
    time_map = time.time() - start

    print(f"--- {testname} - glb testing", flush=True)
    start = time.time()
    if use_fp:
        buildkite_call(["aha", "test", test, "--dense-fp"], env=env_vars)
    else:
        buildkite_call(["aha", "test", test], env=env_vars)
    time_test = time.time() - start

    return time_compile, time_map, time_test


def dispatch(args, extra_args=None):
    seed_flow = not args.non_seed_flow
    use_pipeline = args.use_pipeline
    pipeline_num = args.pipeline_num
    using_matrix_unit = args.using_matrix_unit
    mu_datawidth = args.mu_datawidth
    unroll = args.unroll

    # Preserve backward compatibility
    if args.config == "daily":
        args.config = "pr_aha"  # noqa
    if args.config == "pr":
        args.config = "pr_submod"  # noqa

    from aha.util.regress_tests.tests import Tests
    imported_tests = None

    # For sparse tests, we cherry pick some representative tests to run
    no_zircon_sparse_tests = [
        "vec_elemmul",
        "mat_vecmul_ij",
        "mat_elemadd_leakyrelu_exp",
        "matmul_ikj",
        "tensor3_mttkrp",
    ]

    # pr_aha1 starts with the pr_aha suite and remove some tests
    if args.config == "pr_aha1":
        no_zircon_sparse_tests = []  # Only aha3 does the default sparse tests
        imported_tests = Tests("pr_aha")

        # Define all tests to remove for pr_aha1
        glb_tests_RV_to_remove = ["apps/gaussian_RV", "tests/bit8_packing_test_RV", "tests/bit8_unpack_test_RV", "tests/fp_get_shared_exp_test_RV"]
        glb_tests_fp_RV_to_remove = ["apps/abs_max_full_unroll_fp_RV", "apps/scalar_reduction_fp_RV", "apps/vector_reduction_fp_RV"]
        glb_tests_to_remove = ["tests/bit8_packing_test", "tests/bit8_unpack_test", "tests/fp_get_shared_exp_test", "tests/fp_e8m0_quant_test", "apps/camera_pipeline_2x2",]
        glb_tests_fp_to_remove = ["apps/scalar_max_fp", "apps/stable_softmax_pass2_fp", "apps/stable_softmax_pass3_fp", "apps/scalar_avg_fp",
                                  "apps/layer_norm_pass2_fp", "apps/layer_norm_pass3_fp", "apps/gelu_pass1_fp", "apps/gelu_pass2_fp",
                                  "apps/silu_pass1_fp", "apps/silu_pass2_fp", "apps/swiglu_pass2_fp"]
        resnet_tests_to_remove = ["conv2_x"]
        hardcoded_dense_tests_to_remove = ["apps/unsharp_RV"]

        # Remove integer RV tests
        for test in glb_tests_RV_to_remove:
            if test in imported_tests.glb_tests_RV:
                imported_tests.glb_tests_RV.remove(test)

        # Remove fp RV tests
        for test in glb_tests_fp_RV_to_remove:
            if test in imported_tests.glb_tests_fp_RV:
                imported_tests.glb_tests_fp_RV.remove(test)

        # Remove hardcoded dense tests
        for test in hardcoded_dense_tests_to_remove:
            if test in imported_tests.hardcoded_dense_tests:
                imported_tests.hardcoded_dense_tests.remove(test)

        # Remove integer static tests
        for test in glb_tests_to_remove:
            if test in imported_tests.glb_tests:
                imported_tests.glb_tests.remove(test)

        # Remove fp static tests
        for test in glb_tests_fp_to_remove:
            if test in imported_tests.glb_tests_fp:
                imported_tests.glb_tests_fp.remove(test)

        # Remove integer static resnet tests
        for test in resnet_tests_to_remove:
            if test in imported_tests.resnet_tests:
                imported_tests.resnet_tests.remove(test)

    # pr_aha2 contains part of the remaining tests
    elif args.config == "pr_aha2":
        no_zircon_sparse_tests = []  # Only aha3 does the default sparse tests
        imported_tests = Tests("BLANK")
        imported_tests.glb_tests_RV = ["apps/gaussian_RV"]
        imported_tests.glb_tests_fp_RV = ["apps/abs_max_full_unroll_fp_RV", "apps/scalar_reduction_fp_RV"]
        # We know gaussian is redundant here but we keep it for some reasons
        imported_tests.glb_tests = ["apps/gaussian", "tests/bit8_packing_test", "tests/bit8_unpack_test", "tests/fp_get_shared_exp_test", "tests/fp_e8m0_quant_test"]
        imported_tests.glb_tests_fp = ["apps/scalar_max_fp", "apps/stable_softmax_pass2_fp", "apps/stable_softmax_pass3_fp", "apps/scalar_avg_fp",
                                  "apps/layer_norm_pass2_fp", "apps/layer_norm_pass3_fp"]
        imported_tests.resnet_tests = ["conv2_x"]

    # pr_aha3 contains all the remaining tests
    elif args.config == "pr_aha3":
        imported_tests = Tests("BLANK")
        imported_tests.glb_tests_RV = ["tests/bit8_packing_test_RV", "tests/bit8_unpack_test_RV", "tests/fp_get_shared_exp_test_RV"]
        imported_tests.glb_tests_fp_RV = ["apps/vector_reduction_fp_RV"]
        imported_tests.glb_tests = ["apps/camera_pipeline_2x2"]
        imported_tests.glb_tests_fp = ["apps/gelu_pass1_fp", "apps/gelu_pass2_fp", "apps/silu_pass1_fp", "apps/silu_pass2_fp", "apps/swiglu_pass2_fp"]
        imported_tests.hardcoded_dense_tests = ["apps/unsharp_RV"]
        # imported_tests.resnet_tests_fp = [ 'conv2_x_fp' ]

    # For configs 'fast', 'pr_aha', 'pr_submod', 'full', 'resnet', see regress_tests/tests.py
    else:
        imported_tests = Tests(args.config)

    # Unpack imported_tests into convenient handles
    width, height = imported_tests.width, imported_tests.height
    num_fabric_cols_removed, mu_oc_0 = imported_tests.cols_removed, imported_tests.mu_oc_0
    sparse_tests = imported_tests.sparse_tests
    glb_tests = imported_tests.glb_tests
    glb_tests_fp = imported_tests.glb_tests_fp
    glb_tests_RV = imported_tests.glb_tests_RV
    glb_tests_fp_RV = imported_tests.glb_tests_fp_RV
    resnet_tests = imported_tests.resnet_tests
    resnet_tests_fp = imported_tests.resnet_tests_fp
    hardcoded_dense_tests = imported_tests.hardcoded_dense_tests

    E64_supported_tests = imported_tests.E64_supported_tests
    E64_MB_supported_tests = imported_tests.E64_MB_supported_tests

    # No zircon flag (generate default layout)
    if args.no_zircon:
        print(f"\n\n---- NO-ZIRCON 1 ----\n\n")
        using_matrix_unit = False
        num_fabric_cols_removed = 0
        mu_oc_0 = 0

    else:
        print(f"\033[92mINFO: Using a ZIRCON layout with {num_fabric_cols_removed} fabric columns removed.\033[0m")
        print(f"----ZIRCON LAYOUT INFO----")
        print(f"Tile array width: {width - num_fabric_cols_removed}")
        print(f"Tile array height: {height}")
        print(f"Num GLB tiles: {int (width/2)}")
        print(f"MU OC 0: {mu_oc_0}")
        print(f"--------------------------\n")

        # Verify legality of num_fabric_cols_removed, OC_0
        assert num_fabric_cols_removed % 4 == 0, "ERROR: Number of cols removed must be a multiple of 4"
        assert num_fabric_cols_removed <= width - 4, "ERROR: Removing too many columns. There will be no columns left in the CGRA. Please adjust num_fabric_cols_removed and/or CGRA width."
        assert mu_oc_0 <= 2 * (width - num_fabric_cols_removed), "ERROR: OC_0 cannot be greater than 2 * num CGRA cols. Please double-check OC_0, num_fabric_cols_removed, and CGRA width"

    print(f"--- Running regression: {args.config}", flush=True)
    info = []
    t = gen_garnet(width, height, dense_only=False, using_matrix_unit=using_matrix_unit, mu_datawidth=mu_datawidth, num_fabric_cols_removed=num_fabric_cols_removed, mu_oc_0=mu_oc_0)
    info.append(["garnet (Zircon) with sparse and dense", t])

    data_tile_pairs = []
    kernel_name = ""

    if not(seed_flow):
        if os.path.exists("/aha/garnet/perf_stats.txt"):
            os.system("rm /aha/garnet/perf_stats.txt")
        with open("/aha/garnet/perf_stats.txt", 'w') as perf_out_file:
            perf_out_file.write("SPARSE TEST        SS DATASET        TOTAL RUNTIME (ns)\n\n")

        test_dataset_runtime_dict = {}

        data_tile_pairs_lists = []
        for sparse_tile_pairs_list in args.sparse_tile_pairs_list:
            data_tile_pairs_lists.extend(glob.glob(sparse_tile_pairs_list))

        for data_tile_pairs_file in data_tile_pairs_lists:
            with open(data_tile_pairs_file, 'r') as f:
                tile_pairs_dict = toml.load(f)
                data_tile_pairs = tile_pairs_dict["sam_config"]["sam_path"]
                kernel_name = tile_pairs_dict["sam_config"]["name"]

            print("HERE ARE THE DATA TILE PAIRS!")
            print(data_tile_pairs)

            generate_sparse_bitstreams(sparse_tests, width, height, seed_flow, data_tile_pairs, kernel_name,
                                        opal_workaround=args.opal_workaround, unroll=unroll, using_matrix_unit=using_matrix_unit, num_fabric_cols_removed=num_fabric_cols_removed)

            for test in sparse_tests:
                if use_pipeline:
                    assert (not seed_flow), "Pipeline mode is not supported with seed flow"
                    tile_pairs, pipeline_num_l = format_concat_tiles(test, data_tile_pairs, kernel_name, pipeline_num, unroll)
                    t0, t1, t2 = test_sparse_app(test, seed_flow, tile_pairs, pipeline_num_l, opal_workaround=args.opal_workaround, test_dataset_runtime_dict=test_dataset_runtime_dict,
                                                    using_matrix_unit=using_matrix_unit, mu_datawidth=mu_datawidth, num_fabric_cols_removed=num_fabric_cols_removed, mu_oc_0=mu_oc_0)
                    info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
                else:
                    # calling this function to append the id to the input matrix, find a better way to do so in the future
                    tile_pairs, pipeline_num_l = format_concat_tiles(test, data_tile_pairs, kernel_name, 1, unroll)
                    t0, t1, t2 = test_sparse_app(test, seed_flow, tile_pairs, opal_workaround=args.opal_workaround, test_dataset_runtime_dict=test_dataset_runtime_dict,
                                                    using_matrix_unit=using_matrix_unit, mu_datawidth=mu_datawidth, num_fabric_cols_removed=num_fabric_cols_removed, mu_oc_0=mu_oc_0)
                    info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

                # remove the generated collateral for tiles that passed to avoid overrunning the disk
                os.system(f"rm -rf /aha/garnet/SPARSE_TESTS/{test}*")
                os.system(f"rm /aha/garnet/SPARSE_TESTS/tensor_X*")

        with open("/aha/garnet/perf_stats.txt", 'a') as perf_out_file:
            for testname, dataset_runtime_dict in test_dataset_runtime_dict.items():
                for dataset, time_value in dataset_runtime_dict.items():
                    perf_out_file.write(f"{testname}        {dataset}        {time_value}\n")
    else:
        generate_sparse_bitstreams(sparse_tests, width, height, seed_flow, data_tile_pairs, kernel_name,
                                    opal_workaround=args.opal_workaround, unroll=unroll, using_matrix_unit=using_matrix_unit, num_fabric_cols_removed=num_fabric_cols_removed)

        for test in sparse_tests:
            assert(not use_pipeline), "Pipeline mode is not supported with seed flow"
            t0, t1, t2 = test_sparse_app(test, seed_flow, data_tile_pairs, opal_workaround=args.opal_workaround,
                                            using_matrix_unit=using_matrix_unit, mu_datawidth=mu_datawidth, num_fabric_cols_removed=num_fabric_cols_removed, mu_oc_0=mu_oc_0)
            info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    # Dense ready-valid mode
    def parse_RV_mode(testname):
        dense_ready_valid = False
        if "_RV" in testname:
            dense_ready_valid = True
            testname = test.replace("_RV", "")
        return testname, dense_ready_valid

    # E64 mode
    def parse_E64_mode(testname):
        E64_mode_on = False
        if "_E64" in testname:
            E64_mode_on = True
            testname = test.replace("_E64", "")
        return testname, E64_mode_on

    # E64 MB mode
    def parse_E64_MB_mode(testname):
        E64_multi_bank_mode_on = False
        if "_MB" in testname:
            E64_multi_bank_mode_on = True
            testname = test.replace("_MB", "")
        return testname, E64_multi_bank_mode_on

    def feature_support_check(testname, E64_mode_on, E64_multi_bank_mode_on):
        if E64_mode_on:
            assert testname in E64_supported_tests, f"ERROR: E64 mode not yet supported for {testname}. Please make the necessary changes in Halide-to-Hardware and application_parameters.json. See pointwise for example. Ensure that the E64 unroll is multiple of 4. Once done, please add the test to E64_supported_tests in regress_tests/tests.py"

        if E64_multi_bank_mode_on:
            assert testname in E64_MB_supported_tests, f"ERROR: E64 multi-bank mode not yet supported for {testname}. Please make the necessary changes in Halide-to-Hardware and application_parameters.json. See pointwise for example. Ensure that the E64_MB unroll is multiple of 8. Once done, please add the test to E64_MB_supported_tests in regress_tests"
            assert E64_mode_on, f"ERROR: E64 multi-bank mode requires E64 mode to be enabled. Please add _E64 to the test name"

    # For Zircon, we run all dense apps in RV mode, i.e. glb_tests_RV and glb_tests_fp_RV
    for test in glb_tests_RV:
        test, dense_ready_valid = parse_RV_mode(test)
        test, E64_mode_on = parse_E64_mode(test)
        test, E64_multi_bank_mode_on = parse_E64_MB_mode(test)
        feature_support_check(test, E64_mode_on, E64_multi_bank_mode_on)
        t0, t1, t2 = test_dense_app(test, width, height, args.env_parameters, extra_args,
                        using_matrix_unit=using_matrix_unit, mu_datawidth=mu_datawidth, num_fabric_cols_removed=num_fabric_cols_removed, mu_oc_0=mu_oc_0,
                        dense_ready_valid=dense_ready_valid, E64_mode_on=E64_mode_on, E64_multi_bank_mode_on=E64_multi_bank_mode_on)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in glb_tests_fp_RV:
        test, dense_ready_valid = parse_RV_mode(test)
        test, E64_mode_on = parse_E64_mode(test)
        test, E64_multi_bank_mode_on = parse_E64_MB_mode(test)
        feature_support_check(test, E64_mode_on, E64_multi_bank_mode_on)
        t0, t1, t2 = test_dense_app(test, width, height, args.env_parameters, extra_args, use_fp=True,
                        using_matrix_unit=using_matrix_unit, mu_datawidth=mu_datawidth, num_fabric_cols_removed=num_fabric_cols_removed, mu_oc_0=mu_oc_0,
                        dense_ready_valid=dense_ready_valid, E64_mode_on=E64_mode_on, E64_multi_bank_mode_on=E64_multi_bank_mode_on)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    for test in hardcoded_dense_tests:
        test, dense_ready_valid = parse_RV_mode(test)
        test, E64_mode_on = parse_E64_mode(test)
        test, E64_multi_bank_mode_on = parse_E64_MB_mode(test)
        feature_support_check(test, E64_mode_on, E64_multi_bank_mode_on)
        t0, t1, t2 = test_hardcoded_dense_app(test, width, height, args.env_parameters, extra_args,
                        using_matrix_unit=using_matrix_unit, mu_datawidth=mu_datawidth, num_fabric_cols_removed=num_fabric_cols_removed, mu_oc_0=mu_oc_0,
                        dense_ready_valid=dense_ready_valid, E64_mode_on=E64_mode_on, E64_multi_bank_mode_on=E64_multi_bank_mode_on)
        info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

    if args.include_no_zircon_tests:
        exit_status = os.system(f"rm /aha/garnet/garnet.v")
        if os.WEXITSTATUS(exit_status) != 0:
            raise RuntimeError(f"Command 'rm /aha/garnet/garnet.v' returned non-zero exit status {os.WEXITSTATUS(exit_status)}.")

        print(f"\n\n---- NO-ZIRCON 1 ----\n\n")
        t = gen_garnet(width, height, dense_only=False, using_matrix_unit=False, num_fabric_cols_removed=0)
        info.append(["garnet (NO Zircon) with sparse and dense", t])

        if no_zircon_sparse_tests:
            # See above for no_zircon_sparse_tests[]
            data_tile_pairs = []
            kernel_name = ""
            seed_flow = True
            generate_sparse_bitstreams(no_zircon_sparse_tests, width, height,
                                       seed_flow, data_tile_pairs, kernel_name,
                                       opal_workaround=args.opal_workaround, unroll=unroll)

            for test in no_zircon_sparse_tests:
                t0, t1, t2 = test_sparse_app(test, seed_flow, data_tile_pairs, opal_workaround=args.opal_workaround)
                info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

        # For dense tests, we run glb_tests, glb_tests_fp, resnet_tests, and resnet_tests_fp
        for test in glb_tests:
            t0, t1, t2 = test_dense_app(test, width, height, args.env_parameters, extra_args, dense_only=False, using_matrix_unit=False, num_fabric_cols_removed=0,
                        dense_ready_valid=False, E64_mode_on=False)
            info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

        for test in glb_tests_fp:
            t0, t1, t2 = test_dense_app(test, width, height, args.env_parameters, extra_args, use_fp=True, dense_only=False, using_matrix_unit=False, num_fabric_cols_removed=0,
                        dense_ready_valid=False, E64_mode_on=False)
            info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

        for test in resnet_tests:
            if "residual" in test:
                t0, t1, t2 = test_dense_app("apps/resnet_residual", width, height, args.env_parameters, extra_args, layer=test,
                            dense_only=False, using_matrix_unit=False, num_fabric_cols_removed=0, dense_ready_valid=False, E64_mode_on=False)
                info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
            else:
                t0, t1, t2 = test_dense_app("apps/resnet_output_stationary", width, height, args.env_parameters, extra_args, layer=test,
                            dense_only=False, using_matrix_unit=False, num_fabric_cols_removed=0, dense_ready_valid=False, E64_mode_on=False)
                info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])

        for test in resnet_tests_fp:
            if "residual" in test:
                t0, t1, t2 = test_dense_app("apps/conv2D_residual_fp", width, height, args.env_parameters, extra_args, layer=test, use_fp=True,
                            dense_only=False, using_matrix_unit=False, num_fabric_cols_removed=0, dense_ready_valid=False, E64_mode_on=False)
                info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2])
            else:
                t0, t1, t2 = test_dense_app("apps/conv2D_fp", width, height, args.env_parameters, extra_args, layer=test, use_fp=True,
                            dense_only=False, using_matrix_unit=False, num_fabric_cols_removed=0, dense_ready_valid=False, E64_mode_on=False)
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
            t0, t1, t2 = test_dense_app(test, width, height, args.env_parameters, extra_args, dense_only=True)
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
