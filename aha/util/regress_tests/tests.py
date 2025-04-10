class Tests:

    def __init__(self, testname, zircon=True):
        use_custom = False

        # Defaults

        width, height = 28, 16  # default
        cols_removed, mu_oc_0 = 8, 32

        sparse_tests = []
        glb_tests = []
        glb_tests_fp = []
        resnet_tests = []
        resnet_tests_fp = []
        hardcoded_dense_tests = []

        DRV_supported_tests = [
            "apps/pointwise", "apps/pointwise_mu_io"
        ]
        E64_supported_tests = [
            "apps/pointwise", "apps/pointwise_mu_io", "conv5_x"
        ]
        E64_MB_supported_tests = [
            "apps/pointwise", "apps/pointwise_mu_io"
        ]
        # FAST test suite should complete in just a minute or two
        if testname == "fast":
            width, height = 4, 4
            sparse_tests = [
                "vec_identity"
            ]
            glb_tests = [
                "apps/pointwise",
                "apps/pointwise_RV_E64",
                "apps/pointwise_RV_E64_MB",
            ]
            glb_tests_fp = [
                "tests/fp_pointwise",
            ]
            resnet_tests = [
            ]
            resnet_tests_fp = []
            hardcoded_dense_tests = []

            # New for zircon
            # TODO need to scrub through remaining tests and add "if zircon" clauses for RV, MB etc.!!!
            # OR (more hacky) could do "if not zircon delete RV/MB from all groups kinda thing..."
            if zircon:
                width, height = 8, 8,
                cols_removed, mu_oc_0 = 4, 8
                glb_tests += [
                    "apps/pointwise_RV_E64",
                    "apps/pointwise_RV_E64_MB",
                ]


        # PR_AHA test suite for aha-repo push/pull
        elif testname == "pr_aha":

            # aha pull requests used to invoke the much larger "daily"
            # suite; which we deleted. Now, aha PRs invoke this pared-down
            # test "pr_aha", (as recommended by Kalhan et al.).  Pr_aha is
            # kind of an enhanced version of the old "pr" suite of tests,
            # which was used by pull requests from AHA submodule repos.
            # The old "pr" suite is now called "pr_submod". (Pr_submod
            # only takes a couple of hours whereas pr_aha is in the 8-10
            # hour range.)

            # 2. THEN we broke the 8-10 hour "pr_aha" test into three 3-hour
            # tests pr_aha1,2,3 that can all run in parallel.

            width, height = 28, 16
            cols_removed, mu_oc_0 = 8, 32
            sparse_tests = [
                "vec_elemmul",
                "mat_vecmul_ij",
                "mat_elemadd_leakyrelu_exp",
                "mat_elemdiv",
                "mat_mattransmul",
                "fp_relu_matmul_ikj",
                "matmul_ikj",
                "matmul_jik",
                "fp_relu_spmm_ijk_crddrop",
                "spmv_relu",
                "masked_broadcast",
                "mat_sddmm",
                "tensor3_mttkrp",
                "tensor3_ttv",
            ]
            glb_tests = [
                "apps/maxpooling",
                "apps/pointwise",
                "apps/pointwise_RV",
                "apps/pointwise_E64",
                # "apps/pointwise_E64_MB",
                "apps/pointwise_RV_E64",
                "apps/pointwise_RV_E64_MB",
                "apps/pointwise_mu_io_RV_E64",
                "apps/pointwise_mu_io_RV_E64_MB",
                "apps/gaussian",
                "apps/harris_color",
                "apps/unsharp",
                "apps/camera_pipeline_2x2",
                "tests/bf2int8_pack_test",
            ]
            glb_tests_fp = [
                "tests/int8tobf_unpack_test",
                "apps/matrix_multiplication_fp",
                "apps/scalar_max_fp",
                "apps/stable_softmax_pass2_fp",
                "apps/stable_softmax_pass3_fp",
                "apps/scalar_avg_fp",
                "apps/layer_norm_pass2_fp",
                "apps/layer_norm_pass3_fp",
                "apps/gelu_pass1_fp",
                "apps/gelu_pass2_fp",
                "apps/silu_pass1_fp",
                "apps/silu_pass2_fp",
                "apps/swiglu_pass2_fp",
            ]
            resnet_tests = [
                "conv1",
                "conv2_x",
                "conv5_x_E64",
            ]
            resnet_tests_fp = [
                # "conv2_x_fp" # not yet supported by zircon
            ]
            hardcoded_dense_tests = [
                # "apps/depthwise_conv" # down on Zircon
            ]

# Found the better way maybe
#
#         # PR_AHA tests broken into three sub-parts: aha_pr1
#         elif testname == "pr_aha1":
#             t = Tests('aha_pr')
#
#             # FIXME surely there is a better way of doing this part...!!
#             width, height = (t.width, t.height)
#             sparse_tests = t.sparse_tests
#             glb_tests = t.glb_tests
#             glb_tests_fp = t.glb_tests_fp
#             resnet_tests = t.resnet_tests
#             resnet_tests_fp = t.resnet_tests_fp
#             hardcoded_dense_tests = t.hardcoded_dense_tests
#
#             # Remove conv2 benchmarks, which take about 1.5 hr each...
#             resnet_tests.remove('conv2_x')  # This is actually *two* tests
#             resnet_tests_fp.remove('conv2_x_fp')
#
#         # PR_AHA tests broken into three sub-parts: aha_pr2
#         elif testname == 'pr_aha2':
#             glb_tests = ["apps/gaussian"]  # conv2 breaks if don't do gaussian first :(
#             resnet_tests = [ 'conv2_x' ]   # This is actually *two* tests
#
#         # PR_AHA tests broken into three sub-parts: aha_pr2
#         elif testname == 'pr_aha3':
#             glb_tests = ["apps/gaussian"]  # conv2 breaks if don't do gaussian first :(
#             resnet_tests_fp = [ 'conv2_x_fp' ]

        # PR_SUBMOD tests for push/pull from aha submod repos
        elif testname == "pr_submod":

            # This is the OLD / original two-hour submod pr, I think, from
            # 611c8bb4, before I mucked things up...before that, this set
            # of tests was called simply "pr"

            width, height = 28, 16
            cols_removed, mu_oc_0 = 8, 32
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
                "fp_relu_matmul_ijk_crddrop",
                # Turned off until SUB ordering fixed in mapping
                # 'mat_residual',
                "mat_vecmul_iter",
                "tensor3_elemadd",
                "tensor3_ttm",
                "tensor3_ttv",
            ]
            glb_tests = [
                "apps/pointwise",
                "apps/pointwise_RV",
                "apps/pointwise_E64",
                # "apps/pointwise_E64_MB",
                "apps/pointwise_RV_E64",
                "apps/pointwise_RV_E64_MB",
                "apps/pointwise_mu_io_RV_E64",
                "apps/pointwise_mu_io_RV_E64_MB",
                "tests/ushift",
                "tests/arith",
                "tests/absolute",
                "tests/scomp",
                "tests/ucomp",
                "tests/uminmax",
                "tests/rom",
                "tests/conv_1_2",
                "tests/conv_2_1",
                "tests/bf2int8_pack_test",
            ]
            glb_tests_fp = [
                "tests/int8tobf_unpack_test",
                "tests/fp_pointwise",
                "tests/fp_arith",
                "tests/fp_comp",
                "tests/fp_conv_7_7",
                "apps/scalar_max_fp",
                "apps/stable_softmax_pass2_fp",
                "apps/stable_softmax_pass3_fp",
                "apps/scalar_avg_fp",
                "apps/layer_norm_pass2_fp",
                "apps/layer_norm_pass3_fp",
                "apps/gelu_pass1_fp",
                "apps/gelu_pass2_fp",
                "apps/silu_pass1_fp",
                "apps/silu_pass2_fp",
                "apps/swiglu_pass2_fp",
            ]
            resnet_tests = []
            resnet_tests_fp = []
            hardcoded_dense_tests = [
                # "apps/depthwise_conv" # down on Zircon
            ]

        # FULL test is used by scheduled weekly aha regressions
        elif testname == "full":

            width, height = 28, 16
            cols_removed, mu_oc_0 = 8, 32
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
                "mat_elemdiv",
                "mat_identity",
                "mat_mattransmul",
                "matmul_ijk",
                "matmul_ijk_crddrop",
                "matmul_ikj",
                "matmul_jik",
                "spmm_ijk_crddrop",
                "spmv",
                "spmv_relu",
                "masked_broadcast",
                "trans_masked_broadcast",
                "mat_dn2sp",
                "mat_sp2dn",
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
                "fp_relu_matmul_ijk_crddrop",
                "fp_relu_matmul_ikj",
                "fp_spmm_ijk_crddrop",
                "fp_spmm_ikj",
                "fp_relu_spmm_ijk_crddrop",
                "fp_relu_spmm_ikj",
                "fp_matmul_ijk_crddrop",
                "fp_matmul_ikj",
            ]
            glb_tests = [
                "apps/maxpooling",
                "apps/pointwise",
                "apps/pointwise_RV",
                "apps/pointwise_E64",
                # "apps/pointwise_E64_MB",
                "apps/pointwise_RV_E64",
                "apps/pointwise_RV_E64_MB",
                "apps/pointwise_mu_io_RV_E64",
                "apps/pointwise_mu_io_RV_E64_MB",
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
                "tests/bf2int8_pack_test",
                "apps/gaussian",
                "apps/brighten_and_blur",
                "apps/cascade",
                "apps/harris",
                "apps/resnet_layer_gen",
                "apps/unsharp",
                "apps/harris_color",
                "apps/camera_pipeline_2x2",
                "apps/matrix_multiplication"
            ]
            glb_tests_fp = [
                "apps/maxpooling_fp",
                "tests/fp_pointwise",
                "tests/fp_arith",
                "tests/fp_comp",
                "tests/fp_conv_7_7",
                "tests/int8tobf_unpack_test",
                "apps/matrix_multiplication_fp",
                "apps/scalar_max_fp",
                "apps/stable_softmax_pass2_fp",
                "apps/stable_softmax_pass3_fp",
                "apps/scalar_avg_fp",
                "apps/layer_norm_pass2_fp",
                "apps/layer_norm_pass3_fp",
                "apps/gelu_pass1_fp",
                "apps/gelu_pass2_fp",
                "apps/silu_pass1_fp",
                "apps/silu_pass2_fp",
                "apps/swiglu_pass2_fp",
                # "apps/mcunet_in_sequential_0_fp", # not yet supported by zircon
                # "apps/depthwise_conv_stream_fp", # not yet supported by zircon
            ]

            # FIXME would it be better here to do e.g.
            # resnet_tests = Tests('resnet').resnet_tests ?

            resnet_tests = [
                "conv1",
                "conv2_x",
                "conv5_x_E64",
            ]
            resnet_tests_fp = [
                # "conv2_x_fp", # not yet supported by zircon
                "sequential_0_fp",
                "InvRes1_pw_fp",
                "InvRes2_pw_exp_fp",
                "InvRes2_pw_sq_fp",
                "InvRes3_pw_exp_fp",
                "InvRes3_pw_sq_residual_fp"
            ]
            hardcoded_dense_tests = [
                # "apps/depthwise_conv" # down on Zircon
            ]
        elif testname == "resnet":
            width, height = 28, 16
            cols_removed, mu_oc_0 = 8, 32
            sparse_tests = []
            glb_tests = []
            glb_tests_fp = []
            resnet_tests = [
                "conv1",
                "conv2_x",
                "conv5_x_E64",
            ]
            resnet_tests_fp = []
            hardcoded_dense_tests = []

        # BLANK can be used to return default height, width, and blank test lists
        elif testname == "BLANK":
            pass

        else:
            use_custom = True

        self.width, self.height = width, height
        self.cols_removed, self.mu_oc_0 = cols_removed, mu_oc_0
        self.sparse_tests = sparse_tests
        self.glb_tests = glb_tests
        self.glb_tests_fp = glb_tests_fp
        self.resnet_tests = resnet_tests
        self.resnet_tests_fp = resnet_tests_fp
        self.hardcoded_dense_tests = hardcoded_dense_tests
        self.E64_supported_tests = E64_supported_tests
        self.DRV_supported_tests = DRV_supported_tests
        self.E64_MB_supported_tests = E64_MB_supported_tests

        if use_custom:
            # Read a custom suite from external file <testname>.py
            # E.g. if we build a config file '/aha/aha/util/regress_tests/custom4485.py'
            # "if True:
            #     width, height = 4, 2
            #     glb_tests = [ 'tests/pointwise' ]"
            # then 'aha regress custom4485' would run a 4x2 pointwise test.
            try:
                # Update self parms w those found in custom config {testname}.py
                import importlib
                tmpmodule = importlib.import_module('aha.util.regress_tests.' + testname)
                self.__dict__.update(tmpmodule.__dict__)
            except:
                raise NotImplementedError(
                    f"Cannot find custom config /aha/aha/util/regress_tests/{testname}.py"
                )

    def show_suite(self, suite_name='', zircon=True):
        # Dump regression suite contents in compact form e.g. show_suite('fast'):
        # 
        # fast    sparse_tests   vec_identity             8x8 --removed 4 --mu 8
        # fast    glb_tests      apps/pointwise           8x8 --removed 4 --mu 8
        # fast    glb_tests      apps/pointwise_RV_E64    8x8 --removed 4 --mu 8
        # fast    glb_tests      apps/pointwise_RV_E64_MB 8x8 --removed 4 --mu 8
        # fast    glb_tests_fp   tests/fp_pointwise       8x8 --removed 4 --mu 8

        d = self.__dict__
        size = "%sx%s" % (d['width'], d['height'])
        zparms = " --removed %s --mu %s" % (d["cols_removed"], d["mu_oc_0"])
        if zircon: parms = size + zparms
        else:      parms = size + ' --no-zircon'

        not_groups = ("width", "height", "cols_removed", "mu_oc_0")
        for group in d:
            if not d[group]:               continue  # Dont care about empty sets
            if group in not_groups:        continue  # Not a group
            if "supported_tests" in group: continue  # Also not a group
            for app in d[group]:
                fmt = "%-12s %-16s %-32s %-s"
                print(fmt % (suite_name, group, app, parms))
                # rval += (fmt % (suite_name, group, app, d["app_parms"]))
