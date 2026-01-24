import sys, os
from pathlib import Path
import subprocess
import glob
import toml
from aha.util.regress_tests.tests import Tests

from aha.util.regress_util import gen_garnet
from aha.util.regress_util import generate_sparse_bitstreams
from aha.util.regress_util import format_concat_tiles
from aha.util.regress_util import test_sparse_app
from aha.util.regress_util import test_dense_app
from aha.util.regress_util import test_hardcoded_dense_app
from aha.util.regress_util import info

global info

def report_ongoing_failures(failed_tests):
    if failed_tests:
        print(f"+++ {len(failed_tests)} FAILED TESTS SO FAR")
        for ft in failed_tests: print("  ", ft)

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

def dispatch(args, extra_args=None):
  try:
    seed_flow = not args.non_seed_flow
    use_pipeline = args.use_pipeline
    using_matrix_unit = args.using_matrix_unit
    mu_datawidth = args.mu_datawidth
    unroll = args.unroll

    failed_tests = []
    final_error = None

    # It's painful if we don't catch this up front! (E.g. missing vcs.)
    if "TOOL" in os.environ: TOOL = os.environ["TOOL"].lower()
    else: TOOL = 'vcs'
    p = subprocess.run(
        f'set -x; command -v {TOOL}',
        shell=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    if p.returncode:
        print(f"\n***ERROR Cannot find verilog simulator '{TOOL}'")
        exit(p.returncode)

    imported_tests = None

    # For printing info at the end...
    global info  # HA!
    # info = []  # DON'T DO THIS!!! Or else you lose your pointer to the One True Info in regress_util
    info.clear()

    # For config definitions see regress_tests/tests.py
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
    voyager_cgra_tests_fp = imported_tests.voyager_cgra_tests_fp
    behavioral_mu_tests = imported_tests.behavioral_mu_tests
    behavioral_mu_tests_fp = imported_tests.behavioral_mu_tests_fp
    external_mu_tests = imported_tests.external_mu_tests
    external_mu_tests_fp = imported_tests.external_mu_tests_fp
    hardcoded_dense_tests = imported_tests.hardcoded_dense_tests
    no_zircon_sparse_tests = imported_tests.no_zircon_sparse_tests

#     E64_supported_tests = imported_tests.E64_supported_tests
#     E64_MB_supported_tests = imported_tests.E64_MB_supported_tests

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

    ZIRCON_TAPEOUT_MU_OC0 = 32
    ZIRCON_TAPEOUT_OC_PER_CGRA_COL = 2
    if width - num_fabric_cols_removed < (ZIRCON_TAPEOUT_MU_OC0 // ZIRCON_TAPEOUT_OC_PER_CGRA_COL):
        print(f"\033[93mINFO: CGRA width ({width - num_fabric_cols_removed}) is less than the ZIRCON tapeout width ({ZIRCON_TAPEOUT_MU_OC0 // ZIRCON_TAPEOUT_OC_PER_CGRA_COL}). Hence, the external matrix unit will NOT be included in the simulation.\033[0m")
        if using_matrix_unit:
            os.environ["BEHAVIORAL_MATRIX_UNIT"] = "1"
        assert imported_tests.external_mu_tests == [], "ERROR: External matrix unit tests are not supported for CGRA widths less than the ZIRCON tapeout width. Please remove external_mu_tests from the test list."
        assert imported_tests.external_mu_tests_fp == [], "ERROR: External matrix unit tests are not supported for CGRA widths less than the ZIRCON tapeout width. Please remove external_mu_tests_fp from the test list."

    print(f"--- Running regression: {args.config}", flush=True)

    # Skip 20 minutes of gen_garnet if no tests exist for it!!!
    zircon_tests_exist = False
    if [
            *sparse_tests,
            *glb_tests_RV,
            *glb_tests_fp_RV,
            *voyager_cgra_tests_fp,
            *behavioral_mu_tests,
            *behavioral_mu_tests_fp,
            *external_mu_tests,
            *external_mu_tests_fp,
            *hardcoded_dense_tests
    ]:
        t = gen_garnet(width, height, dense_only=False, using_matrix_unit=using_matrix_unit, mu_datawidth=mu_datawidth, num_fabric_cols_removed=num_fabric_cols_removed, mu_oc_0=mu_oc_0)
        info.append(["garnet (Zircon) with sparse and dense", t])

    data_tile_pairs = []
    kernel_name = ""

    info.append([f"APP GROUP sparse_tests[]", 0])
    if sparse_tests and not(seed_flow):
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

            t = generate_sparse_bitstreams(
                sparse_tests, width, height, seed_flow, data_tile_pairs, kernel_name,
                opal_workaround=args.opal_workaround,
                unroll=unroll,
                using_matrix_unit=using_matrix_unit,
                num_fabric_cols_removed=num_fabric_cols_removed,
                mu_oc_0=mu_oc_0)
            info.append(["gen_sparse_bitstreams", t, 0, t, 0])  # Count this as "map" time

            for test in sparse_tests:
                if use_pipeline:
                    assert (not seed_flow), "Pipeline mode is not supported with seed flow"
                    tile_pairs, pipeline_num_l = format_concat_tiles(
                        test, data_tile_pairs, kernel_name, args.pipeline_num, unroll)
                else:
                    # calling this function to append the id to the input matrix,
                    # find a better way to do so in the future
                    tile_pairs, pipeline_num_l = format_concat_tiles(
                        test, data_tile_pairs, kernel_name, 1, unroll)
                    pipeline_num_l = None

                t0, t1, t2, t3, t4, t5 = test_sparse_app(
                    test, seed_flow, tile_pairs,
                    pipeline_num_l=pipeline_num_l,
                    opal_workaround=args.opal_workaround,
                    test_dataset_runtime_dict=test_dataset_runtime_dict,
                    using_matrix_unit=using_matrix_unit,
                    mu_datawidth=mu_datawidth,
                    num_fabric_cols_removed=num_fabric_cols_removed,
                    mu_oc_0=mu_oc_0)
                info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2, t3, t4, t5])

                # remove the generated collateral for tiles that passed to avoid overrunning the disk
                os.system(f"rm -rf /aha/garnet/SPARSE_TESTS/{test}*")
                os.system(f"rm /aha/garnet/SPARSE_TESTS/tensor_X*")

        with open("/aha/garnet/perf_stats.txt", 'a') as perf_out_file:
            for testname, dataset_runtime_dict in test_dataset_runtime_dict.items():
                for dataset, time_value in dataset_runtime_dict.items():
                    perf_out_file.write(f"{testname}        {dataset}        {time_value}\n")

    elif sparse_tests:
        t = generate_sparse_bitstreams(
            sparse_tests, width, height, seed_flow, data_tile_pairs, kernel_name,
            opal_workaround=args.opal_workaround,
            unroll=unroll,
            using_matrix_unit=using_matrix_unit,
            num_fabric_cols_removed=num_fabric_cols_removed,
            mu_oc_0=mu_oc_0)
        info.append(["gen_sparse_bitstreams", t, 0, t, 0])  # Count this as "map" time

        for test in sparse_tests:
            assert(not use_pipeline), "Pipeline mode is not supported with seed flow"
            t0, t1, t2, t3, t4, t5 = test_sparse_app(
                test, seed_flow, data_tile_pairs,
                opal_workaround=args.opal_workaround,
                using_matrix_unit=using_matrix_unit,
                mu_datawidth=mu_datawidth,
                num_fabric_cols_removed=num_fabric_cols_removed,
                mu_oc_0=mu_oc_0)
            info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2, t3, t4, t5])

    for test in [
            ('glb_tests_RV',        '_glb'),           *glb_tests_RV,
            ('glb_tests_fp_RV',     '_glb'),           *glb_tests_fp_RV,
            ('behavioral_mu_tests', '_MU_behavioral'), *behavioral_mu_tests,
            ('behavioral_mu_tests_fp', '_MU_behavioral'), *behavioral_mu_tests_fp,
            ('voyager_cgra_tests_fp','_voyager_standalone_cgra'), *voyager_cgra_tests_fp,
            ('external_mu_tests',   '_MU_ext'),        *external_mu_tests,
            ('external_mu_tests_fp','_MU_ext'),        *external_mu_tests_fp]:

        if type(test) is tuple:
            tgroup,tsuffix = test
            print(f"--- Processing app group {tgroup}", flush=True)
            info.append([f"APP GROUP {tgroup}[]", 0])
            continue

        unparsed_name = test

        try:
            t0, t1, t2, t3, t4, t5 = test_dense_app(
                test, tgroup, width, height, args.env_parameters, extra_args,
                using_matrix_unit=using_matrix_unit, mu_datawidth=mu_datawidth,
                num_fabric_cols_removed=num_fabric_cols_removed, mu_oc_0=mu_oc_0
            )
            info.append([unparsed_name+tsuffix, t0+t1+t2, t0, t1, t2, t3, t4, t5])

        except Exception as e:
            print(f"--- FAILED TEST {unparsed_name}:\n{e}")
            failed_tests += [unparsed_name]
            final_error = e
            info.append([unparsed_name+tsuffix+" FAIL"])

        report_ongoing_failures(failed_tests)

    print(f"--- Processing app group hardcoded_dense_tests", flush=True)
    info.append(["APP GROUP hardcoded_dense_tests[]", 0])
    for test in hardcoded_dense_tests:
        unparsed_name = test
        t0, t1, t2, t3, t4, t5 = test_hardcoded_dense_app(test, width, height, args.env_parameters, extra_args,
                        using_matrix_unit=using_matrix_unit, mu_datawidth=mu_datawidth,
                        num_fabric_cols_removed=num_fabric_cols_removed, mu_oc_0=mu_oc_0)
        info.append([unparsed_name + "_glb", t0 + t1 + t2, t0, t1, t2, t3, t4, t5])
        report_ongoing_failures(failed_tests)

    # Skip unnecessary garnet build if tests don't exist, duh.
    tests_exist = True if [
        *no_zircon_sparse_tests,
        *glb_tests,
        *glb_tests_fp,
        *resnet_tests,
        *resnet_tests_fp,
    ] else False

    if args.include_no_zircon_tests and tests_exist:

        # Want new garnet.v and gen_garnet() will NOT build it if one exists already (!)
        # Use 'rm -f' b/c don't want error when/if garnet.v is already gone...
        exit_status = os.system(f"rm -f /aha/garnet/garnet.v")
        if os.WEXITSTATUS(exit_status) != 0:
            raise RuntimeError(f"Command 'rm -f /aha/garnet/garnet.v' returned non-zero exit status {os.WEXITSTATUS(exit_status)}.")

        print(f"\n\n---- NO-ZIRCON 1 ----\n\n")
        t = gen_garnet(width, height, dense_only=False, using_matrix_unit=False, num_fabric_cols_removed=0)
        info.append(["garnet (NO Zircon) with sparse and dense", t])
        report_ongoing_failures(failed_tests)

        if no_zircon_sparse_tests:
            # See above for no_zircon_sparse_tests[]
            data_tile_pairs = []
            kernel_name = ""
            seed_flow = True
            t = generate_sparse_bitstreams(no_zircon_sparse_tests, width, height,
                                       seed_flow, data_tile_pairs, kernel_name,
                                       opal_workaround=args.opal_workaround, unroll=unroll)
            info.append(["gen_sparse_bitstreams_nz", t, 0, t, 0])  # Count this as "map" time
            report_ongoing_failures(failed_tests)

            for test in no_zircon_sparse_tests:
                t0, t1, t2, t3, t4, t5 = test_sparse_app(test, seed_flow, data_tile_pairs, opal_workaround=args.opal_workaround)
                info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2, t3, t4, t5])
                report_ongoing_failures(failed_tests)

        # For dense tests, we run glb_tests, glb_tests_fp, resnet_tests, and resnet_tests_fp

        for test in [
            ('glb_tests',       '_glb'), *glb_tests,
            ('glb_tests_fp',    '_glb'), *glb_tests_fp,
            ('resnet_tests',    '_glb'), *resnet_tests,
            ('resnet_tests_fp', '_glb'), *resnet_tests_fp]:

            if type(test) is tuple:
                tgroup,tsuffix = test
                print(f"--- Processing app group {tgroup}", flush=True)
                info.append([f"APP GROUP {tgroup}[]", 0])
                continue

            t0, t1, t2, t3, t4, t5 = test_dense_app(test, tgroup, width, height, args.env_parameters, extra_args)
            info.append([test + "_glb", t0 + t1 + t2, t0, t1, t2, t3, t4, t5])
            report_ongoing_failures(failed_tests)

    # Skip unnecessary garnet build if tests don't exist, duh.
    dense_only_tests_exist = True if glb_tests else False
    for test in resnet_tests:
        if "residual" not in test: dense_only_tests_exist = True

    if args.include_dense_only_tests and dense_only_tests_exist:
        # DENSE ONLY TESTS
        # Remove sparse+dense garnet.v first
        exit_status = os.system(f"rm -f /aha/garnet/garnet.v")
        if os.WEXITSTATUS(exit_status) != 0:
            raise RuntimeError(f"Command 'rm -f /aha/garnet/garnet.v' returned non-zero exit status {os.WEXITSTATUS(exit_status)}.")

        t = gen_garnet(width, height, dense_only=True)
        info.append(["garnet with dense only", t])
        report_ongoing_failures(failed_tests)

        num_dense_only_glb_tests = 5
        for test_index, test in enumerate(glb_tests):
            if test_index == num_dense_only_glb_tests:
                break
            t0, t1, t2, t3, t4, t5 = test_dense_app(test, width, height, args.env_parameters, extra_args, dense_only=True)
            info.append([test + "_glb dense only", t0 + t1 + t2, t0, t1, t2, t3, t4, t5])
            report_ongoing_failures(failed_tests)

        for test in resnet_tests:
            # residual resnet test is not working with dense only mode
            if "residual" not in test:
                t0, t1, t2, t3, t4, t5 = test_dense_app("apps/resnet_output_stationary",
                                            width, height, args.env_parameters, extra_args, layer=test)
                info.append([test + "_glb dense only", t0 + t1 + t2, t0, t1, t2, t3, t4, t5])
                report_ongoing_failures(failed_tests)

  except Exception as e:
      final_error = e

  finally:
    from tabulate import tabulate
    sys.stderr.flush()
    print(f"+++ TIMING INFO", flush=True)
    print(tabulate(info, headers=["step", "total", "compile", "map", "test", "active app cyc.", "config cyc.", "wdata cyc."], floatfmt=".0f"), flush=True)

    if failed_tests:
        print(f"+++ FAILURES", flush=True)
        for ft in failed_tests: print("  ", ft)

    if final_error:
        raise(final_error)


def gather_tests(tags):
    pass
