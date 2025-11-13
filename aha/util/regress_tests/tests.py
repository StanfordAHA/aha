# Find and/or install pyyaml
from subprocess import run, DEVNULL
run('python3 -m pip install pyyaml', shell=True, stdout = DEVNULL, stderr = DEVNULL)
import json, yaml

########################################################################
class Tests:

    # Valid configs as of Oct 2025:
    #   "fast"    quick and dirty ten-minute test of basic apps
    #
    #   "pr_aha1" thru "pr_aha9"
    #             regression tests that run on every aha pull, takes about 6-8 hours
    #
    #   "pr_aha"  combines all tests pr_aha1-9 into a single group
    #
    #   "full"    extensive set of apps that run for 30 hours every sunday night
    #
    #   "resnet"  three resnet tests---does anyone still use this?
    #
    #   "mu"      bunch of "external_mu_tests", mostly resnet18
    #
    #   "BLANK"   returns empty set of all test groups, useful for initializing a new group

    configs_list = ["fast", "pr_aha1", "pr_aha2", "pr_aha3", "pr_aha4",
                 "pr_aha5", "pr_aha6", "pr_aha7", "pr_aha8", "pr_aha9",
                 "pr_aha", "full", "resnet", "mu", "BLANK"]

    def configs_template():
        # Defaults
        width, height = 28, 16  # default
        sparse_tests = []
        glb_tests_RV = []
        glb_tests_fp_RV = []
        glb_tests = []
        glb_tests_fp = []
        resnet_tests = []
        resnet_tests_fp = []
        # voyager_cgra_tests_fp = []
        behavioral_mu_tests = []
        external_mu_tests = []
        external_mu_tests_fp = []
        hardcoded_dense_tests = []
        no_zircon_sparse_tests = []

        # Zircon specific parms; 'regress.py --no-zircon' ignores these
        cols_removed, mu_oc_0 = 12, 32

        E64_supported_tests = [
            "apps/pointwise",
            "apps/pointwise_mu_io",
            "conv5_x",
            "apps/avgpool_layer_fp",
            "apps/mat_vec_mul_fp",
            "apps/maxpooling_dense_rv_fp",
            "apps/fully_connected_layer_fp",
            "apps/pointwise_custom_packing",
            "apps/pointwise_custom_place_multibank",
            "apps/get_e8m0_scale_test_fp",
            "apps/get_apply_e8m0_scale_fp",
            "apps/zircon_residual_relu_fp",
            "apps/zircon_nop",
            "apps/zircon_psum_reduction_fp",
            "apps/zircon_dequantize_relu_fp",
            "apps/zircon_dequant_fp",
            "apps/zircon_deq_ResReLU_quant_fp",
            "apps/zircon_deq_q_relu_fp",
            "apps/zircon_deq_ResReLU_fp",
            "apps/zircon_res_deq_ReLU_quant_fp",
            "apps/zircon_quant_fp",
            "apps/mu2glb_path_balance_test",
        ]
        E64_MB_supported_tests = [
            "apps/pointwise",
            "apps/pointwise_mu_io",
            "apps/pointwise_custom_place_multibank",
            "apps/get_e8m0_scale_test_fp",
            "apps/get_apply_e8m0_scale_fp",
            "apps/avgpool_layer_fp",
            "apps/mat_vec_mul_fp",
            "apps/maxpooling_dense_rv_fp",
            "apps/fully_connected_layer_fp",
            "apps/zircon_residual_relu_fp",
            "apps/zircon_nop",
            "apps/zircon_psum_reduction_fp",
            "apps/zircon_dequantize_relu_fp",
            "apps/zircon_dequant_fp",
            "apps/zircon_deq_ResReLU_quant_fp",
            "apps/zircon_deq_q_relu_fp",
            "apps/zircon_deq_ResReLU_fp",
            "apps/zircon_res_deq_ReLU_quant_fp",
            "apps/zircon_quant_fp",
            "apps/mu2glb_path_balance_test",
        ]
        vardic = vars().copy()

        # Include any and all groups defined in groups() method
        g = Tests.groups().copy()
        for key in g: vardic[key] = []
        return vardic

    def groups():
        voyager_cgra_tests_fp = [

            "subgroup1",
            # Standalone quantize layers
            "resnet18-quantize_default_1::zircon_quant_fp_post_conv2x_RV_E64_MB",
            "resnet18-quantize_default_3::zircon_quant_fp_post_conv2x_RV_E64_MB",
            "resnet18-quantize_default_7::zircon_quant_fp_post_conv3x_RV_E64_MB",
            "resnet18-quantize_default_11::zircon_quant_fp_post_conv4x_RV_E64_MB",
            "resnet18-quantize_default_15::zircon_quant_fp_post_conv5x_RV_E64_MB",

            "subgroup2",
            # Average pooling layer
            "resnet18-adaptive_avg_pool2d_default_1::avgpool_layer_fp_RV_E64_MB",

            "subgroup3",
            # Fully connected layer (K-DIM HOST TILING)
            "resnet18-linear::fully_connected_layer_fp_kernel0_RV_E64_MB",
            "resnet18-linear::fully_connected_layer_fp_kernel1_RV_E64_MB",
        ]
        return vars().copy()

    def __init__(self, testname="BLANK", zircon=True):
        self.__dict__.update(Tests.configs_template())

        # Simplify: use pr_aha instead of "pr", "daily", or "pr_submod"
        if testname in ["daily", "pr", "pr_submod"]:
            print(f'WARNING "{testname}" config no longer exists, using "pr_aha" instead')
            config = "pr_aha"


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

        elif testname == "pr_aha1":

            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
            sparse_tests = [
                # pr_aha1
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
            self.addgroup("voyager_cgra_tests_fp", [1])
            external_mu_tests_fp = [
                # Conv1 (im2col-based, X-DIM HOST TILING)
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB",
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB",
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel2_RV_E64_MB",
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel3_RV_E64_MB",
            ]
        elif testname == "pr_aha2":
            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
            external_mu_tests_fp = [
                # Conv2_x
                "resnet18-submodule_2 -> zircon_deq_q_relu_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_3 -> zircon_deq_ResReLU_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_4 -> zircon_deq_q_relu_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_5 -> zircon_deq_ResReLU_quant_fp_post_conv2_x_RV_E64_MB",
            ]
        elif testname == "pr_aha3":
            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
            external_mu_tests_fp = [
                # Conv3_1 strided conv
                "resnet18-submodule_6 -> zircon_deq_q_relu_fp_post_conv3_1_RV_E64_MB",

                # Conv3_1 pointwise conv
                "resnet18-submodule_7 -> zircon_dequant_fp_post_conv3_1_RV_E64_MB",

                # Conv3_x
                "resnet18-submodule_8 -> zircon_deq_ResReLU_fp_post_conv3_x_RV_E64_MB",
                "resnet18-submodule_9 -> zircon_deq_q_relu_fp_post_conv3_x_RV_E64_MB",
                "resnet18-submodule_10 -> zircon_deq_ResReLU_quant_fp_post_conv3_x_RV_E64_MB",
            ]

        elif testname == "pr_aha4":
            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
            glb_tests_RV = [
                "tests/conv_2_1_RV",
                "tests/fp_e8m0_quant_test_RV",
                "apps/pointwise_RV",
                "apps/pointwise_RV_E64",
                "apps/pointwise_RV_E64_MB",
                "apps/pointwise_custom_packing_RV_E64",
                "apps/gaussian_RV",
                "tests/bit8_packing_test_RV",
                "tests/bit8_unpack_test_RV",
                "tests/fp_get_shared_exp_test_RV",
                "apps/maxpooling_dense_rv_fp_RV_E64_MB",
            ]
            behavioral_mu_tests = [
                "apps/pointwise_mu_io_RV_E64",
                "apps/pointwise_mu_io_RV_E64_MB",
                "apps/mu2glb_path_balance_test_RV_E64",
                "apps/abs_max_full_unroll_fp_RV",
                "apps/get_e8m0_scale_test_fp_RV_E64_MB",
                "apps/get_apply_e8m0_scale_fp_RV_E64_MB",
            ]
            external_mu_tests_fp = [
                # Conv4_1 strided conv (TILED OUTER REDUCTION WORKAROUND)
                "resnet18-submodule_11 -> zircon_nop_tiled_outer_reduction_workaround_post_conv4_1_RV_E64_MB",
                "resnet18-submodule_11 -> zircon_res_deq_ReLU_quant_fp_tiled_outer_reduction_workaround_post_conv4_1_RV_E64_MB",

                # Conv4_1 pointwise conv (INNER REDUCTION WORKAROUND)
                "resnet18-submodule_12 -> zircon_dequant_fp_post_conv4_1_inner_reduction_workaround_RV_E64_MB",
            ]
            hardcoded_dense_tests = [
                "apps/unsharp_RV",
            ]
        elif testname == "pr_aha5":
            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
            # For sparse tests, we cherry pick some representative tests to run
            no_zircon_sparse_tests = [
                "vec_elemmul",
                "mat_vecmul_ij",
                "mat_elemadd_leakyrelu_exp",
                "matmul_ikj",
                "tensor3_mttkrp",
            ]
            # Tests below are non-zircon and won't run by default
            glb_tests = [
                "apps/pointwise",
                "apps/maxpooling",
                "tests/bit8_packing_test",
                "tests/bit8_unpack_test",
                "tests/fp_get_shared_exp_test",
                "tests/fp_e8m0_quant_test",
                "apps/camera_pipeline_2x2",
                "apps/gaussian",
                "apps/harris_color",
                "apps/unsharp",
            ]
            glb_tests_fp = [
                "tests/fp_arith",
                "tests/fp_comp",
                "apps/matrix_multiplication_fp",
                "apps/relu_layer_fp",
                "apps/scalar_max_fp",
                "apps/scalar_avg_fp",
            ]
            external_mu_tests_fp = [
                # Conv4_x
                "resnet18-submodule_13 -> zircon_deq_ResReLU_fp_post_conv4_x_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_deq_q_relu_fp_post_conv4_x_RV_E64_MB",
                "resnet18-submodule_15 -> zircon_deq_ResReLU_quant_fp_post_conv4_x_RV_E64_MB",
            ]
        elif testname == "pr_aha6":
            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
            resnet_tests = [
                "conv1",
                "conv2_x",
                "conv5_x",
            ]
            resnet_tests_fp = [
                # "conv2_x_fp" # not yet supported by zircon
            ]
        elif testname == "pr_aha7":
            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
            external_mu_tests_fp = [
                # Conv5_1 strided Conv (INPUT ACTIVATION PADDING WORKAROUND)
                "resnet18-submodule_16 -> zircon_deq_q_relu_fp_post_conv5_1_RV_E64_MB",

                # Conv5_1 pointwise conv (INNER REDUCTION WORKAROUND, INPUT ACTIVATION PADDING WORKAROUND)
                "resnet18-submodule_17 -> zircon_dequant_fp_post_conv5_1_inner_reduction_workaround_RV_E64_MB",

                # Conv5_x (K-DIM HOST TILING, INPUT ACTIVATION PADDING WORKAROUND)
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel1_RV_E64_MB",
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel2_RV_E64_MB",
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel3_RV_E64_MB",
            ]
        elif testname == "pr_aha8":
            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
            glb_tests_fp_RV = [
                "tests/fp_arith_RV",
                "tests/fp_comp_RV",
                "apps/relu_layer_fp_RV",
                "apps/relu_layer_multiout_fp_RV",
                "apps/mat_vec_mul_fp_RV_E64_MB",
                "apps/scalar_reduction_fp_RV",
                "apps/scalar_max_fp_RV",
                "apps/layer_norm_pass2_fp_RV",
                "apps/layer_norm_pass3_fp_RV",
                "apps/scalar_avg_fp_RV",
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
            self.addgroup("voyager_cgra_tests_fp", [2,3])

        elif testname == "pr_aha9":
            width, height = 28, 16
            cols_removed, mu_oc_0 = 12, 32
            external_mu_tests_fp = [
                # Conv5_x (K-DIM HOST TILING, INPUT ACTIVATION PADDING WORKAROUND)
                "resnet18-submodule_19 -> zircon_deq_q_relu_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_19 -> zircon_deq_q_relu_fp_post_conv5_x_kernel1_RV_E64_MB",

                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel1_RV_E64_MB",
                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel2_RV_E64_MB",
                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel3_RV_E64_MB",
            ]

        # PR_AHA test suite for aha-repo push/pull;
        # build pr_aha1,2,3 and then merge them all together
        elif testname == "pr_aha":
            def merge_tests(s1, s2):
                for key in s2:
                    if type(s2[key]) is list:
                        s1[key] = list(dict.fromkeys(s1[key] + s2[key]))  # Removes dupes AND preserves list order
                    else:
                        # Non-lists (e.g. width, height) should be same for both sets
                        assert s1[key] == s2[key], f'Found different values for "{key}" among pr_aha1,2,3'

            pr_aha = Tests('pr_aha1').__dict__
            merge_tests(pr_aha, Tests('pr_aha2').__dict__)
            merge_tests(pr_aha, Tests('pr_aha3').__dict__)
            merge_tests(pr_aha, Tests('pr_aha4').__dict__)
            merge_tests(pr_aha, Tests('pr_aha5').__dict__)
            merge_tests(pr_aha, Tests('pr_aha6').__dict__)
            merge_tests(pr_aha, Tests('pr_aha7').__dict__)
            merge_tests(pr_aha, Tests('pr_aha8').__dict__)
            merge_tests(pr_aha, Tests('pr_aha9').__dict__)
            self.__dict__.update(pr_aha)
            # print(f"{self.resnet_tests=}", flush=True)
            return

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
                "apps/maxpooling_dense_rv_fp_RV_E64_MB",
            ]
            glb_tests_fp_RV = [
                "apps/relu_layer_fp_RV",
                "apps/relu_layer_multiout_fp_RV",
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
                "apps/mat_vec_mul_fp_RV_E64_MB",
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
            self.addgroup("voyager_cgra_tests_fp")
            behavioral_mu_tests = [
                "apps/pointwise_mu_io_RV_E64",
                "apps/pointwise_mu_io_RV_E64_MB",
                "apps/mu2glb_path_balance_test_RV_E64",
                "apps/abs_max_full_unroll_fp_RV",
                "apps/get_e8m0_scale_test_fp_RV_E64_MB",
                "apps/get_apply_e8m0_scale_fp_RV_E64_MB",
            ]
            external_mu_tests = [

            ]
            external_mu_tests_fp = [
                # Conv1 (im2col-based, X-DIM HOST TILING)
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB",
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB",
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel2_RV_E64_MB",
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel3_RV_E64_MB",

                # Conv2_x
                "resnet18-submodule_2 -> zircon_deq_q_relu_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_3 -> zircon_deq_ResReLU_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_4 -> zircon_deq_q_relu_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_5 -> zircon_deq_ResReLU_quant_fp_post_conv2_x_RV_E64_MB",

                # Conv3_1 strided conv
                "resnet18-submodule_6 -> zircon_deq_q_relu_fp_post_conv3_1_RV_E64_MB",

                # Conv3_1 pointwise conv
                "resnet18-submodule_7 -> zircon_dequant_fp_post_conv3_1_RV_E64_MB",

                # Conv3_x
                "resnet18-submodule_8 -> zircon_deq_ResReLU_fp_post_conv3_x_RV_E64_MB",
                "resnet18-submodule_9 -> zircon_deq_q_relu_fp_post_conv3_x_RV_E64_MB",
                "resnet18-submodule_10 -> zircon_deq_ResReLU_quant_fp_post_conv3_x_RV_E64_MB",

                # Conv4_1 strided conv (TILED OUTER REDUCTION WORKAROUND)
                "resnet18-submodule_11 -> zircon_nop_tiled_outer_reduction_workaround_post_conv4_1_RV_E64_MB",
                "resnet18-submodule_11 -> zircon_res_deq_ReLU_quant_fp_tiled_outer_reduction_workaround_post_conv4_1_RV_E64_MB",

                # Conv4_1 pointwise conv (INNER REDUCTION WORKAROUND)
                "resnet18-submodule_12 -> zircon_dequant_fp_post_conv4_1_inner_reduction_workaround_RV_E64_MB",

                # Conv4_x
                "resnet18-submodule_13 -> zircon_deq_ResReLU_fp_post_conv4_x_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_deq_q_relu_fp_post_conv4_x_RV_E64_MB",
                "resnet18-submodule_15 -> zircon_deq_ResReLU_quant_fp_post_conv4_x_RV_E64_MB",

                # Conv5_1 strided Conv (INPUT ACTIVATION PADDING WORKAROUND)
                "resnet18-submodule_16 -> zircon_deq_q_relu_fp_post_conv5_1_RV_E64_MB",

                # Conv5_1 pointwise conv (INNER REDUCTION WORKAROUND, INPUT ACTIVATION PADDING WORKAROUND)
                "resnet18-submodule_17 -> zircon_dequant_fp_post_conv5_1_inner_reduction_workaround_RV_E64_MB",

                # Conv5_x (K-DIM HOST TILING, INPUT ACTIVATION PADDING WORKAROUND)
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel1_RV_E64_MB",
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel2_RV_E64_MB",
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel3_RV_E64_MB",

                "resnet18-submodule_19 -> zircon_deq_q_relu_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_19 -> zircon_deq_q_relu_fp_post_conv5_x_kernel1_RV_E64_MB",

                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel1_RV_E64_MB",
                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel2_RV_E64_MB",
                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel3_RV_E64_MB",
            ]

            # For sparse tests, we cherry pick some representative tests to run
            no_zircon_sparse_tests = [
                "vec_elemmul",
                "mat_vecmul_ij",
                "mat_elemadd_leakyrelu_exp",
                "matmul_ikj",
                "tensor3_mttkrp",
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
            self.addgroup("voyager_cgra_tests_fp")
            behavioral_mu_tests = [
                "apps/mu2glb_path_balance_test_RV_E64",
                "apps/pointwise_mu_io_RV_E64_MB",
            ]
            external_mu_tests = [
            ]
            external_mu_tests_fp = [
                # Conv1 (im2col-based, X-DIM HOST TILING)
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB",
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB",
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel2_RV_E64_MB",
                "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel3_RV_E64_MB",

                # Conv2_x
                "resnet18-submodule_2 -> zircon_deq_q_relu_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_3 -> zircon_deq_ResReLU_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_4 -> zircon_deq_q_relu_fp_post_conv2_x_RV_E64_MB",
                "resnet18-submodule_5 -> zircon_deq_ResReLU_quant_fp_post_conv2_x_RV_E64_MB",

                # Conv3_1 strided conv
                "resnet18-submodule_6 -> zircon_deq_q_relu_fp_post_conv3_1_RV_E64_MB",

                # Conv3_1 pointwise conv
                "resnet18-submodule_7 -> zircon_dequant_fp_post_conv3_1_RV_E64_MB",

                # Conv3_x
                "resnet18-submodule_8 -> zircon_deq_ResReLU_fp_post_conv3_x_RV_E64_MB",
                "resnet18-submodule_9 -> zircon_deq_q_relu_fp_post_conv3_x_RV_E64_MB",
                "resnet18-submodule_10 -> zircon_deq_ResReLU_quant_fp_post_conv3_x_RV_E64_MB",

                # Conv4_1 strided conv (TILED OUTER REDUCTION WORKAROUND)
                "resnet18-submodule_11 -> zircon_nop_tiled_outer_reduction_workaround_post_conv4_1_RV_E64_MB",
                "resnet18-submodule_11 -> zircon_res_deq_ReLU_quant_fp_tiled_outer_reduction_workaround_post_conv4_1_RV_E64_MB",

                # Conv4_1 pointwise conv (INNER REDUCTION WORKAROUND)
                "resnet18-submodule_12 -> zircon_dequant_fp_post_conv4_1_inner_reduction_workaround_RV_E64_MB",

                # Conv4_x
                "resnet18-submodule_13 -> zircon_deq_ResReLU_fp_post_conv4_x_RV_E64_MB",
                "resnet18-submodule_14 -> zircon_deq_q_relu_fp_post_conv4_x_RV_E64_MB",
                "resnet18-submodule_15 -> zircon_deq_ResReLU_quant_fp_post_conv4_x_RV_E64_MB",

                # Conv5_1 strided Conv (INPUT ACTIVATION PADDING WORKAROUND)
                "resnet18-submodule_16 -> zircon_deq_q_relu_fp_post_conv5_1_RV_E64_MB",

                # Conv5_1 pointwise conv (INNER REDUCTION WORKAROUND, INPUT ACTIVATION PADDING WORKAROUND)
                "resnet18-submodule_17 -> zircon_dequant_fp_post_conv5_1_inner_reduction_workaround_RV_E64_MB",

                # Conv5_x (K-DIM HOST TILING, INPUT ACTIVATION PADDING WORKAROUND)
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel1_RV_E64_MB",
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel2_RV_E64_MB",
                "resnet18-submodule_18 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel3_RV_E64_MB",

                "resnet18-submodule_19 -> zircon_deq_q_relu_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_19 -> zircon_deq_q_relu_fp_post_conv5_x_kernel1_RV_E64_MB",

                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel0_RV_E64_MB",
                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel1_RV_E64_MB",
                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel2_RV_E64_MB",
                "resnet18-submodule_20 -> zircon_deq_ResReLU_fp_post_conv5_x_kernel3_RV_E64_MB",
            ]


        # BLANK can be used to return default height, width, and blank test lists
        elif testname == "BLANK":
            pass

        # json strings for app util
        elif self.detect_and_process_json(testname):
            return

        # yaml strings for app util
        elif self.detect_and_process_yaml(testname):
            return

        else: pass

        # Export everything named in template
        vdic = vars().copy()
        for key in Tests.configs_template():
            if key in vdic:
                self.__dict__[key] = vdic[key]

        return


    def prefix_lines(lines, prefix):
        'Attach the indicated prefix to each line in "lines"'
        return prefix + lines.replace('\n', '\n'+prefix)

     # Json string as config e.g. '{"width":8,"height":8,"glb_tests":["apps/pointwise"]}'
    def detect_and_process_json(self, config):
        '''if "config" is a parsable json string, add it to selfdict and return True'''
        try:    config_dict = json.loads(config)
        except: return False
        assert type(config_dict) == dict
        print(f"Found json string:\n{Tests.prefix_lines(config, '    ')}\n")
        self.__dict__.update(config_dict)
        return True

    # Yaml string as config e.g. "width: 8\nheight: 8\nglb_tests:\n- apps/pointwise"
    def detect_and_process_yaml(self, config):
        '''if "config" is a parsable yaml string, add it to selfdict and return True'''
        try:
            config_dict = yaml.safe_load(config)
            assert type(config_dict) == dict
        except: return False
        print(f'{config_dict=}')
        print(f"Found yaml string:\n{Tests.prefix_lines(config, '    ')}\n")
        self.__dict__.update(config_dict)
        return True

    # Support function for app util
    def show_config(config_name='', zircon=True):
        # Dump regression suite contents in compact form e.g. show_config('fast'):
        #
        # fast    sparse_tests   vec_identity             8x8 --removed 4 --mu 8
        # fast    glb_tests      apps/pointwise           8x8 --removed 4 --mu 8
        # fast    glb_tests      apps/pointwise_RV_E64    8x8 --removed 4 --mu 8
        # fast    glb_tests      apps/pointwise_RV_E64_MB 8x8 --removed 4 --mu 8
        # fast    glb_tests_fp   tests/fp_pointwise       8x8 --removed 4 --mu 8

        # Find config and populate it with default keys from template
        d = Tests.configs_template()
        # d.update(Tests.configs[config_name])
        d.update(Tests(config_name).__dict__)

        (w,h) =  (d['width'], d['height'])
        (col,mu) = (d["cols_removed"], d["mu_oc_0"])

        # Setup up the format string for parms e.g. "8x8 --removed 4 --mu 8"
        size = "%sx%s" % (w,h)                       # "8x8"
        zparms = ",--removed %s,--mu %s" % (col,mu)  # "--removed 4 --mu 8"
        if zircon: parms = size + zparms
        else:      parms = size + ',--no-zircon'

        not_groups = ("width", "height", "cols_removed", "mu_oc_0")
        for group in d:
            if not d[group]:               continue  # Dont care about empty sets
            if group in not_groups:        continue  # Not a group
            if "supported_tests" in group: continue  # Also not a group
            for app in d[group]:
                # fmt = "%-12s %-16s %-32s %-s"
                fmt = "%s,%s,%s,%-s"
                print(fmt % (config_name, group, app, parms))
                # rval += (fmt % (config_name, group, app, d["app_parms"]))

    def show_configs(zircon=True):
        for c in Tests.configs_list: Tests.show_config(c)

# Every time someone tries to import this class, it triggers this quick
# to make sure that no configs have redundant apps e.g. if someone accidentally
# puts two copies of 'conv2_x" into the "full" config, this will catch it.

def check_for_dupes(DBG=0):
    errors = ''
    if DBG: print("tests.py: Verify no duplicates in any groups")
    for config_name in Tests.configs_list:
        if DBG: print('\n', config_name)
        config = Tests(config_name).__dict__
        lists = [key for key in config if type(config[key]) is list]
        for group in lists:
            apps = config[group]
            if DBG: print(f'    Config {config_name} has list {group}', end='')
            dbg_result = ' - no dupes (good)'
            for app in set(apps):  # Use set to prevent duplicate checks
                n_app = apps.count(app)
                if n_app > 1:
                    errors += f"    ERROR: Config {config_name}[{group}] has {n_app} copies of '{app}'\n"
                    dbg_result = ' - FOUND DUPES! ERROR!'
            if DBG: print(dbg_result)
    assert not errors, 'Found duplicate apps, see ERROR messages above\n\n' + errors



def addgroup(self, groupname, subgroup=[]):
    '''E.g. addgroup("voyager_cgra_tests_fp", [2,3])'''
    applist = []
    group_info = Tests.groups()[groupname]
    for line in group_info:

        # Subgroup info line e.g. line == "subgroup2"
        if line.startswith('subgroup'):
            sgi = int(line[8:]); continue

        # Default is to include ALL apps
        if not subgroup: applist += [line]

        # If subgroups specified, only include apps in those subgroups
        elif sgi in subgroup: applist += [line]

    self.__dict__['voyager_cgra_tests_fp'] = applist
    return True

Tests.addgroup = addgroup

# def foo():
#     g=Tests.group('voyager_cgra_tests_fp')
#     for app in g: print('   ', app)
#     exit()



#     g=group('voyager_cgra_tests_fp', subgroup=[2,3])
# #     print('---')
#     for app in g: print('   ', app)
#     exit()

# # Tests.foo()
# foo = Tests('pr_aha8').__dict__
# for app in foo['voyager_cgra_tests_fp']: print('        ',app)
# exit()
# for group in foo:
#     print('   ', group)
#     if type(foo[group]) is list:
#         for app in foo[group]: print('        ',app)
# exit()


check_for_dupes(DBG=0)

# app utility uses this to do things like e.g.
#     tests.py --exec "print(*Tests.configs_list)"  # list config names
#     tests.py --exec "for c in Tests.configs_list: Tests.show_config(c)  # list config contents
if __name__ == "__main__":
    import sys
    if '--exec' in sys.argv: exec(sys.argv[2])
