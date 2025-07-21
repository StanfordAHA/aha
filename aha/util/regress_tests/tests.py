class Tests:

    def __init__(self, testname, zircon=True):
        use_custom = False

        # Defaults
        width, height = 28, 16  # default
        sparse_tests = []
        glb_tests_RV = []
        glb_tests_fp_RV = []
        glb_tests = []
        glb_tests_fp = []
        resnet_tests = []
        resnet_tests_fp = []
        behavioral_mu_tests = []
        external_mu_tests = []
        external_mu_tests_fp = []
        hardcoded_dense_tests = []

        # Zircon specific parms; 'regress.py --no-zircon' ignores these
        cols_removed, mu_oc_0 = 12, 32

        E64_supported_tests = [
            "apps/pointwise",
            "apps/pointwise_mu_io",
            "conv5_x",
            "apps/avgpool_layer_fp",
            "apps/pointwise_custom_packing",
            "apps/pointwise_custom_place_multibank",
            "apps/get_e8m0_scale_test_fp",
            "apps/zircon_residual_relu_fp",
            "apps/zircon_nop",
            "apps/zircon_psum_reduction_fp"
        ]
        E64_MB_supported_tests = [
            "apps/pointwise",
            "apps/pointwise_mu_io",
            "apps/pointwise_custom_place_multibank",
            "apps/get_e8m0_scale_test_fp",
            "apps/zircon_residual_relu_fp",
            "apps/zircon_nop",
            "apps/zircon_psum_reduction_fp"
        ]
        # FAST test suite should complete in just a minute or two
        if testname == "fast":
            width, height = 8, 8,
            cols_removed, mu_oc_0 = 4, 8  # Ignored if --no-zircon is set
            sparse_tests = [
                "vec_identity"
            ]
            glb_tests_RV = [
                "tests/conv_2_1_RV",
                "apps/pointwise_RV_E64",
                "apps/pointwise_RV_E64_MB",
            ]
            glb_tests_fp_RV = [
                "tests/fp_pointwise_RV",
            ]
            glb_tests = [
                "apps/pointwise",
            ]
            glb_tests_fp = [
                "tests/fp_pointwise",
            ]
            resnet_tests = []
            resnet_tests_fp = []
            behavioral_mu_tests = []
            external_mu_tests = []
            external_mu_tests_fp = []
            hardcoded_dense_tests = []

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
            cols_removed, mu_oc_0 = 12, 32
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
                "fp_spmm_ijk_crddrop_locator",
                "spmv_relu",
                "masked_broadcast",
                "mat_sddmm",
                "tensor3_mttkrp",
                "tensor3_ttv",
            ]
            glb_tests_RV = [
                # pr_aha1
                "tests/conv_2_1_RV",
                "tests/fp_e8m0_quant_test_RV",
                "apps/pointwise_RV",
                "apps/pointwise_RV_E64",
                "apps/pointwise_RV_E64_MB",
                # pr_aha2
                "apps/gaussian_RV",
                "apps/pointwise_custom_packing_RV_E64",
                # pr_aha3
                "tests/bit8_packing_test_RV",
                "tests/bit8_unpack_test_RV",
                "tests/fp_get_shared_exp_test_RV",
            ]
            glb_tests_fp_RV = [
                # pr_aha1
                "tests/fp_arith_RV",
                "tests/fp_comp_RV",
                "apps/relu_layer_fp_RV",
                "apps/avgpool_layer_fp_RV_E64",
                "apps/mat_vec_mul_fp_RV",
                # pr_aha2
                "apps/scalar_reduction_fp_RV",
                "apps/scalar_max_fp_RV",
                "apps/layer_norm_pass2_fp_RV",
                "apps/layer_norm_pass3_fp_RV",
                "apps/scalar_avg_fp_RV",
                # pr_aha3
                "apps/stable_softmax_pass2_fp_RV",
                "apps/stable_softmax_pass3_fp_RV",
                "apps/vector_reduction_fp_RV",
                "apps/gelu_pass1_fp_RV",
                "apps/gelu_pass2_fp_RV",
                "apps/silu_pass1_fp_RV",
                "apps/silu_pass2_fp_RV",
                "apps/swiglu_pass2_fp_RV",
                "apps/rope_pass1_fp_RV",
                "apps/rope_pass2_fp_RV",
            ]
            hardcoded_dense_tests = [
                # pr_aha3
                "apps/unsharp_RV",
                # "apps/depthwise_conv" # down on Zircon
            ]
            # Tests below are non-zircon and won't run by default
            glb_tests = [
                # pr_aha1
                "apps/pointwise",
                # pr_aha2
                "apps/maxpooling",
                "tests/bit8_packing_test",
                "tests/bit8_unpack_test",
                "tests/fp_get_shared_exp_test",
                "tests/fp_e8m0_quant_test",
                # pr_aha3
                "apps/camera_pipeline_2x2",
                "apps/gaussian",
                "apps/harris_color",
                "apps/unsharp",
            ]
            glb_tests_fp = [
                # pr_aha1
                "tests/fp_arith",
                "tests/fp_comp",
                "apps/matrix_multiplication_fp",
                "apps/relu_layer_fp",
                # pr_aha2
                "apps/scalar_max_fp",
                # pr_aha3
                "apps/scalar_avg_fp",
            ]
            resnet_tests = [
                # pr_aha1
                "conv5_x",
                # pr_aha2
                "conv2_x",
                # pr_aha3
                "conv1",
            ]
            resnet_tests_fp = [
                # "conv2_x_fp" # not yet supported by zircon
            ]
            behavioral_mu_tests = [
                "apps/pointwise_mu_io_RV_E64",
                "apps/pointwise_mu_io_RV_E64_MB",
                "apps/abs_max_full_unroll_fp_RV",
                "apps/get_e8m0_scale_test_fp_RV_E64_MB",
            ]
            external_mu_tests = [
                "resnet18-conv2d_mx_default_6 -> zircon_nop_post_conv3_x_RV_E64_MB",
                "resnet18-conv2d_mx_default_11 -> zircon_nop_post_conv4_x_RV_E64_MB",
                "fakeconv2d-conv2d_mx_default -> zircon_nop_post_fakeconv2d_RV_E64_MB",
            ]
            external_mu_tests_fp = [
                "resnet18-submodule_2 -> zircon_residual_relu_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_6 -> zircon_residual_relu_fp_post_conv3_x_RV_E64_MB",

                # PSUM WORKAROUND CONV4_X downsample
                "resnet18-submodule_10 -> zircon_psum_reduction_fp_post_conv4_x_kernel0_RV_E64_MB",
                "resnet18-submodule_10 -> zircon_residual_relu_fp_post_conv4_x_psum_workaround_RV_E64_MB",

                # PSUM WORKAROUND CONV5_X downsample
                "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel1_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel2_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_residual_relu_fp_post_conv5_x_psum_workaround_RV_E64_MB",
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
            cols_removed, mu_oc_0 = 12, 32
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
            glb_tests_RV = [
                "tests/ushift_RV",
                "tests/arith_RV",
                "tests/absolute_RV",
                "tests/scomp_RV",
                "tests/ucomp_RV",
                "tests/uminmax_RV",
                "tests/rom_RV",
                "tests/conv_2_1_RV",
                "tests/bit8_packing_test_RV",
                "tests/bit8_unpack_test_RV",
                "tests/fp_get_shared_exp_test_RV",
                "tests/fp_e8m0_quant_test_RV",
                "apps/pointwise_RV",
                "apps/pointwise_RV_E64",
                "apps/pointwise_RV_E64_MB",
                "apps/pointwise_custom_packing_RV_E64",
                "apps/gaussian_RV",
                # TODO: Tests below are planned but not yet supported
                # "tests/conv_1_2_RV",
            ]
            glb_tests_fp_RV = [
                "tests/fp_pointwise_RV",
                "tests/fp_arith_RV",
                "tests/fp_comp_RV",
                "apps/relu_layer_fp_RV",
                "apps/scalar_reduction_fp_RV",
                "apps/vector_reduction_fp_RV",
                "apps/scalar_max_fp_RV",
                "apps/stable_softmax_pass2_fp_RV",
                "apps/stable_softmax_pass3_fp_RV",
                "apps/scalar_avg_fp_RV",
                "apps/layer_norm_pass2_fp_RV",
                "apps/layer_norm_pass3_fp_RV",
                "apps/gelu_pass1_fp_RV",
                "apps/gelu_pass2_fp_RV",
                "apps/silu_pass1_fp_RV",
                "apps/silu_pass2_fp_RV",
                "apps/swiglu_pass2_fp_RV",
                "apps/rope_pass1_fp_RV",
                "apps/rope_pass2_fp_RV",
                "apps/avgpool_layer_fp_RV_E64",
                "apps/mat_vec_mul_fp_RV",
                # TODO: Tests below are planned but not yet supported
                # "tests/fp_conv_7_7_RV",
            ]
            hardcoded_dense_tests = [
                "apps/unsharp_RV",
                # "apps/depthwise_conv" # down on Zircon
            ]
            # Tests below are non-zircon and won't run by default
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
                "tests/bit8_packing_test",
                "tests/bit8_unpack_test",
                "tests/fp_get_shared_exp_test",
                "tests/fp_e8m0_quant_test",
            ]
            glb_tests_fp = [
                "tests/fp_pointwise",
                "tests/fp_arith",
                "tests/fp_comp",
                "tests/fp_conv_7_7",
                "apps/relu_layer_fp",
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
                "apps/rope_pass1_fp",
                "apps/rope_pass2_fp",
            ]
            resnet_tests = []
            resnet_tests_fp = []
            behavioral_mu_tests = [
                "apps/pointwise_mu_io_RV_E64",
                "apps/pointwise_mu_io_RV_E64_MB",
                "apps/abs_max_full_unroll_fp_RV",
                "apps/get_e8m0_scale_test_fp_RV_E64_MB",
            ]
            external_mu_tests = [
                "resnet18-conv2d_mx_default_6 -> zircon_nop_post_conv3_x_RV_E64_MB",
                "resnet18-conv2d_mx_default_11 -> zircon_nop_post_conv4_x_RV_E64_MB",
                "fakeconv2d-conv2d_mx_default -> zircon_nop_post_fakeconv2d_RV_E64_MB",
            ]
            external_mu_tests_fp = [
                "resnet18-submodule_2 -> zircon_residual_relu_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_6 -> zircon_residual_relu_fp_post_conv3_x_RV_E64_MB",

                # PSUM WORKAROUND CONV4_X downsample
                "resnet18-submodule_10 -> zircon_psum_reduction_fp_post_conv4_x_kernel0_RV_E64_MB",
                "resnet18-submodule_10 -> zircon_residual_relu_fp_post_conv4_x_psum_workaround_RV_E64_MB",

                # PSUM WORKAROUND CONV5_X downsample
                "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel1_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel2_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_residual_relu_fp_post_conv5_x_psum_workaround_RV_E64_MB",
            ]


        # FULL test is used by scheduled weekly aha regressions
        elif testname == "full":

            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
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
                "fp_spmm_ijk_crddrop_locator",
                "fp_spmm_ikj",
                "fp_relu_spmm_ijk_crddrop",
                "fp_relu_spmm_ikj",
                "fp_matmul_ijk_crddrop",
                "fp_matmul_ikj",
            ]
            glb_tests_RV = [
                "apps/pointwise_RV",
                "apps/pointwise_RV_E64",
                "apps/pointwise_RV_E64_MB",
                "tests/rom_RV",
                "tests/arith_RV",
                "tests/absolute_RV",
                "tests/boolean_ops_RV",
                "tests/equal_RV",
                "tests/ternary_RV",
                "tests/scomp_RV",
                "tests/ucomp_RV",
                "tests/sminmax_RV",
                "tests/uminmax_RV",
                "tests/sshift_RV",
                "tests/ushift_RV",
                "tests/conv_2_1_RV",
                "tests/conv_3_3_RV",
                "tests/bit8_packing_test_RV",
                "tests/bit8_unpack_test_RV",
                "tests/fp_get_shared_exp_test_RV",
                "tests/mem_slice_test_RV",
                "tests/mem_transpose_test_RV",
                "tests/mem_filter_test_RV",
                "tests/fp_e8m0_quant_test_RV",
                "apps/gaussian_RV",
                "apps/brighten_and_blur_RV",
                "apps/pointwise_custom_packing_RV_E64",
                # TODO: Tests below are planned but not yet supported
                # "tests/conv_1_2_RV",
                # "apps/maxpooling_RV",
                # "apps/cascade_RV",
            ]
            glb_tests_fp_RV = [
                "apps/relu_layer_fp_RV",
                "apps/scalar_reduction_fp_RV",
                "apps/vector_reduction_fp_RV",
                "tests/fp_pointwise_RV",
                "tests/fp_arith_RV",
                "tests/fp_comp_RV",
                "apps/scalar_max_fp_RV",
                "apps/stable_softmax_pass2_fp_RV",
                "apps/stable_softmax_pass3_fp_RV",
                "apps/scalar_avg_fp_RV",
                "apps/layer_norm_pass2_fp_RV",
                "apps/layer_norm_pass3_fp_RV",
                "apps/gelu_pass1_fp_RV",
                "apps/gelu_pass2_fp_RV",
                "apps/silu_pass1_fp_RV",
                "apps/silu_pass2_fp_RV",
                "apps/swiglu_pass2_fp_RV",
                "apps/rope_pass1_fp_RV",
                "apps/rope_pass2_fp_RV",
                "apps/avgpool_layer_fp_RV_E64",
                "apps/mat_vec_mul_fp_RV",
                # TODO: Tests below are planned but not yet supported
                # "apps/maxpooling_fp_RV",
                # "tests/fp_conv_7_7_RV",
            ]
            hardcoded_dense_tests = [
                "apps/unsharp_RV",
                # TODO: Tests below are planned but not yet supported
                # "apps/depthwise_conv" # down on Zircon
            ]
            # Tests below are non-zircon and won't run by default
            glb_tests = [
                "apps/maxpooling",
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
                "tests/bit8_packing_test",
                "tests/bit8_unpack_test",
                "tests/fp_get_shared_exp_test",
                "tests/fp_e8m0_quant_test",
                "apps/gaussian",
                "apps/brighten_and_blur",
                "apps/cascade",
                "apps/harris",
                "apps/resnet_layer_gen",
                "apps/unsharp",
                "apps/harris_color",
                "apps/camera_pipeline_2x2",
                "apps/matrix_multiplication",
            ]
            glb_tests_fp = [
                "apps/maxpooling_fp",
                "apps/relu_layer_fp",
                "tests/fp_pointwise",
                "tests/fp_arith",
                "tests/fp_comp",
                "tests/fp_conv_7_7",
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
                "apps/rope_pass1_fp",
                "apps/rope_pass2_fp",
                # TODO: Tests below are planned but not yet supported
                # "apps/mcunet_in_sequential_0_fp", # not yet supported by zircon
                # "apps/depthwise_conv_stream_fp", # not yet supported by zircon
            ]

            # FIXME would it be better here to do e.g.
            # resnet_tests = Tests('resnet').resnet_tests ?

            resnet_tests = [
                "conv1",
                "conv2_x",
                "conv5_x",
            ]
            resnet_tests_fp = [
                "sequential_0_fp",
                "InvRes1_pw_fp",
                "InvRes2_pw_exp_fp",
                "InvRes2_pw_sq_fp",
                "InvRes3_pw_exp_fp",
                "InvRes3_pw_sq_residual_fp",
                # TODO: Tests below are planned but not yet supported
                # "conv2_x_fp", # not yet supported by zircon
            ]
            behavioral_mu_tests = [
                "apps/pointwise_mu_io_RV_E64",
                "apps/pointwise_mu_io_RV_E64_MB",
                "apps/abs_max_full_unroll_fp_RV",
                "apps/get_e8m0_scale_test_fp_RV_E64_MB",
            ]
            external_mu_tests = [
                "resnet18-conv2d_mx_default_6 -> zircon_nop_post_conv3_x_RV_E64_MB",
                "resnet18-conv2d_mx_default_11 -> zircon_nop_post_conv4_x_RV_E64_MB",
                "fakeconv2d-conv2d_mx_default -> zircon_nop_post_fakeconv2d_RV_E64_MB",
            ]
            external_mu_tests_fp = [
                "resnet18-submodule_2 -> zircon_residual_relu_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_6 -> zircon_residual_relu_fp_post_conv3_x_RV_E64_MB",

                # PSUM WORKAROUND CONV4_X downsample
                "resnet18-submodule_10 -> zircon_psum_reduction_fp_post_conv4_x_kernel0_RV_E64_MB",
                "resnet18-submodule_10 -> zircon_residual_relu_fp_post_conv4_x_psum_workaround_RV_E64_MB",

                # PSUM WORKAROUND CONV5_X downsample
                "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel1_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel2_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_residual_relu_fp_post_conv5_x_psum_workaround_RV_E64_MB",
            ]
        elif testname == "resnet":
            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
            sparse_tests = []
            glb_tests = []
            glb_tests_fp = []
            glb_tests_RV = []
            glb_tests_fp_RV = []
            resnet_tests = [
                "conv1",
                "conv2_x",
                "conv5_x",
            ]
            behavioral_mu_tests = []
            external_mu_tests = []
            external_mu_tests_fp = []

        elif testname == "mu":
            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
            sparse_tests = []
            glb_tests = []
            glb_tests_fp = []
            glb_tests_RV = []
            glb_tests_fp_RV = []
            resnet_tests = []
            behavioral_mu_tests = [
                # "apps/pointwise_mu_io_RV_E64",
                # "apps/pointwise_mu_io_RV_E64_MB",
            ]
            external_mu_tests = [
                # "resnet18-conv2d_mx_default_6 -> zircon_nop_post_conv3_x_RV_E64_MB",
                # "resnet18-conv2d_mx_default_11 -> zircon_nop_post_conv4_x_RV_E64_MB",
                # "fakeconv2d-conv2d_mx_default -> zircon_nop_post_fakeconv2d_RV_E64_MB",

                # conv5_x host tiling
                # "resnet18-conv2d_mx_default_16 -> zircon_nop_post_conv5_x_kernel0_RV_E64_MB",
                # "resnet18-conv2d_mx_default_16 -> zircon_nop_post_conv5_x_kernel1_RV_E64_MB",

            ]
            external_mu_tests_fp = [
                # "resnet18-submodule_2 -> zircon_residual_relu_fp_post_conv2_x_RV_E64_MB",
                # "resnet18-submodule_6 -> zircon_residual_relu_fp_post_conv3_x_RV_E64_MB",

                # # PSUM WORKAROUND CONV4_X downsample
                # "resnet18-submodule_10 -> zircon_psum_reduction_fp_post_conv4_x_kernel0_RV_E64_MB",
                # "resnet18-submodule_10 -> zircon_residual_relu_fp_post_conv4_x_psum_workaround_RV_E64_MB",

                # # PSUM WORKAROUND CONV5_X downsample
                # "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel0_RV_E64_MB",
                # "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel1_RV_E64_MB",
                # "resnet18-submodule_14 -> zircon_psum_reduction_fp_post_conv5_x_kernel2_RV_E64_MB",
                # "resnet18-submodule_14 -> zircon_residual_relu_fp_post_conv5_x_psum_workaround_RV_E64_MB",


                # # conv5_x host tiling
                # "resnet18-submodule_16 -> zircon_residual_relu_fp_post_conv5_x_kernel0_RV_E64_MB",
                # "resnet18-submodule_16 -> zircon_residual_relu_fp_post_conv5_x_kernel1_RV_E64_MB",
                # "resnet18-submodule_16 -> zircon_residual_relu_fp_post_conv5_x_kernel2_RV_E64_MB",
                "resnet18-submodule_16 -> zircon_residual_relu_fp_post_conv5_x_kernel3_RV_E64_MB",

            ]


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
        self.glb_tests_RV = glb_tests_RV
        self.glb_tests_fp_RV = glb_tests_fp_RV
        self.resnet_tests = resnet_tests
        self.resnet_tests_fp = resnet_tests_fp
        self.behavioral_mu_tests = behavioral_mu_tests
        self.external_mu_tests = external_mu_tests
        self.external_mu_tests_fp = external_mu_tests_fp
        self.hardcoded_dense_tests = hardcoded_dense_tests
        self.E64_supported_tests = E64_supported_tests
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
