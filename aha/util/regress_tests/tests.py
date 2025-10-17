# SAD that it should come to this...
from subprocess import run, DEVNULL
run(f'python3 -m pip install pyyaml', shell=True,
    stdout = DEVNULL,
    stderr = DEVNULL,
    )
import yaml
import json
'''
TODO
- make regress.py be okay with blank lists
- make it work with "app"
'''

########################################################################
# Helper functions

def combine(dict1, *args):
    '''Given one or more dicts as args, merge them all into one.
       If dict entry is a list, the lists are concatenated.
       Otherwise, entry in rightmost dict takes precedence, and replaces all others.
    '''
    # If no args, return a deep copy of dict1; merge will remove any duplicates.
    if not args:
        args = [dict1]; dict1 = {}

    # Do pairwise merges until done.
    for dict2 in args:
        if type(dict2) is str: dict2 = yaml.safe_load(dict2)
        for key in dict2:
            if key not in dict1:
                dict1[key] = dict2[key]

            elif type(dict2[key]) is list:
                # dict1[key] = list(set(dict1[key] + dict2[key]))          # Removes dupes but does not preserve list order :(
                dict1[key] = list(dict.fromkeys(dict1[key] + dict2[key]))  # Less readable but preserves order oh well
            else:
                if not dict1[key] == dict2[key]:
                    # print(f'Warning: overriding {key}={dict1[key]} with new value {key}={dict2[key]}')
                    dict1[key] = dict2[key] # Replace all others
    return dict1

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
    configs = {}

    # Default groups and values
    template = {
        # CGRA width and height
        'width' : 28,
        'height' : 16,  # default

        # Zircon specific parms; 'regress.py --no-zircon' ignores these
        'cols_removed' : 12,
        'mu_oc_0' : 32,

        # App groups
        'sparse_tests' : [],
        'glb_tests' : [],
        'glb_tests_fp' : [],
        'glb_tests_RV' : [],
        'glb_tests_fp_RV' : [],
        'resnet_tests' : [],
        'resnet_tests_fp' : [],
        'behavioral_mu_tests' : [],
        'external_mu_tests' : [],
        'external_mu_tests_fp' : [],
        'hardcoded_dense_tests' : [],
        'no_zircon_sparse_tests' : [],
    }    

    # ------------------------------------------------------------------------------
    # BLANK config can be used to return default height, width, test group names etc.
    # ------------------------------------------------------------------------------
    configs['BLANK'] = {}

    # ------------------------------------------------------------------------
    # fast (should just take a couple of minutes)
    # ------------------------------------------------------------------------
    configs['fast'] = combine('''
        width: 8
        height: 8
        cols_removed: 4  # Ignored if --no-zircon is set
        mu_oc_0: 8       # Ignored if --no-zircon is set
        sparse_tests:
            - vec_identity
        glb_tests_RV:
            - tests/conv_2_1_RV
            - apps/pointwise_RV_E64
            - apps/pointwise_RV_E64_MB
        glb_tests_fp_RV:
            - tests/fp_pointwise_RV
        glb_tests:
            - apps/pointwise
        glb_tests_fp:
            - tests/fp_pointwise
        '''
    )

    # ------------------------------------------------------------------------
    # mu
    # ------------------------------------------------------------------------
    # - defining w multiple subgroups helps w aha regression load balancing
    # - also helpful are comments with approximate test runtime
    # - times are taken from aha-flow build 12226 unless otherwise noted
    # ------------------------------------------------------------------------
    resnet18_conv2d6 = {  # 46m build 12226
        'external_mu_tests':['resnet18-conv2d_mx_default_6 -> zircon_nop_post_conv3_x_RV_E64_MB']
    }
    resnet18_conv2d11 = {  # 28m build 12226
        'external_mu_tests':['resnet18-conv2d_mx_default_11 -> zircon_nop_post_conv4_x_RV_E64_MB']
    }
    resnet18_conv2dfake = {  # 22m build 12226
        'external_mu_tests':['fakeconv2d-conv2d_mx_default -> zircon_nop_post_fakeconv2d_RV_E64_MB']
    }
    resnet18_conv2d16 = {  # 44m build 12226
        'external_mu_tests':[
            # K-DIM HOST TILING CONV5_X
            'resnet18-conv2d_mx_default_16 -> zircon_nop_post_conv5_x_kernel0_RV_E64_MB',
            'resnet18-conv2d_mx_default_16 -> zircon_nop_post_conv5_x_kernel1_RV_E64_MB',]
    }
    resnet18_zdqr = {  # 82m build 12226
        # X-DIM HOST TILING CONV1 (im2col-based)
        'external_mu_tests_fp': [
            'resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB',
            'resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB',
            'resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel2_RV_E64_MB',
            'resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel3_RV_E64_MB',]
    }
    resnet18_submod3 = {  # 80m build 12226 
        'external_mu_tests_fp': ['resnet18-submodule_3 -> zircon_residual_relu_fp_post_conv2_x_RV_E64_MB']
    }
    resnet18_submod3 = {  # 80m build 12226 
        'external_mu_tests_fp': ['resnet18-submodule_3 -> zircon_residual_relu_fp_post_conv2_x_RV_E64_MB']
    }
    resnet18_submod7 = {  # 52m build 12226
        'external_mu_tests_fp':['resnet18-submodule_7 -> zircon_residual_relu_fp_post_conv3_x_RV_E64_MB']
    }
    resnet18_submod11 = {  # 38m build 12226
        # INNER REDUCTION WORKAROUND CONV4_X downsample
        'external_mu_tests_fp':['resnet18-submodule_11 -> zircon_residual_relu_fp_post_conv4_x_inner_reduction_workaround_RV_E64_MB']
    }
    resnet18_submod15 = {  # 28m build 12226
        # INNER REDUCTION WORKAROUND CONV5_X downsample
        'external_mu_tests_fp':['resnet18-submodule_15 -> zircon_residual_relu_fp_post_conv5_x_inner_reduction_workaround_RV_E64_MB']
    }
    resnet18_submod17 = {  # 94m build 12226
        # K-DIM HOST TILING CONV5_X
        'external_mu_tests_fp': [
            'resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel0_RV_E64_MB',
            'resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel1_RV_E64_MB',
            'resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel2_RV_E64_MB',
            'resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel3_RV_E64_MB',]
    }
    configs['mu'] = combine(
        {
            "height": 16, "width": 28, "mu_oc_0": 32, "cols_removed": 12,
            "behavioral_mu_tests": [
                "apps/pointwise_mu_io_RV_E64",
                "apps/pointwise_mu_io_RV_E64_MB"],
        },
        resnet18_conv2d6,
        resnet18_conv2d11,
        resnet18_conv2dfake,
        resnet18_conv2d16,
        resnet18_zdqr,
        resnet18_submod3,
        resnet18_submod7,
        resnet18_submod11,
        resnet18_submod15,
        resnet18_submod17,
    )

    # ------------------------------------------------------------------------
    # resnet
    # ------------------------------------------------------------------------
    configs['resnet'] = {
        "height": 16, "width": 28, "mu_oc_0": 32, "cols_removed": 12,
        "resnet_tests": [
            "conv1",
            "conv2_x",
            "conv5_x",
        ]
    }

    # ------------------------------------------------------------------------
    # Test-suite subgroups for aha regressions
    # ------------------------------------------------------------------------
    # - defining w multiple subgroups helps w aha regression load balancing
    # - also helpful are comments with approximate test runtime
    # - times are taken from aha-flow build 12226 unless otherwise noted

    # ------------------------------------------------------------------------
    # pr_aha1
    # ------------------------------------------------------------------------
    configs['pr_aha1'] = combine(
        {},
        '''
          sparse_tests:        # 54m build 12226
            - vec_elemmul
            - mat_vecmul_ij
            - mat_elemadd_leakyrelu_exp
            - mat_elemdiv
            - mat_mattransmul
            - fp_relu_matmul_ikj
            - matmul_ikj
            - matmul_jik
            - fp_relu_spmm_ijk_crddrop
            - fp_spmm_ijk_crddrop_locator
            - spmv_relu
            - masked_broadcast
            - mat_sddmm
            - tensor3_mttkrp
            - tensor3_ttv
        ''',
        resnet18_submod17
    )
    # ------------------------------------------------------------------------
    # pr_aha2
    # ------------------------------------------------------------------------
    configs['pr_aha2'] = combine(
        resnet18_submod3,  # 80m
    )
    # ------------------------------------------------------------------------
    # pr_aha3
    # ------------------------------------------------------------------------
    configs['pr_aha3'] = combine(
        resnet18_submod7,   # 52m
        resnet18_submod11,  # 38m
    )
    # ------------------------------------------------------------------------
    # pr_aha4
    # ------------------------------------------------------------------------
    configs['pr_aha4'] = combine(
        {},
        '''glb_tests_RV:  # 56m build 12226
            - tests/conv_2_1_RV
            - tests/fp_e8m0_quant_test_RV
            - apps/pointwise_RV
            - apps/pointwise_RV_E64
            - apps/pointwise_RV_E64_MB
            - apps/pointwise_custom_packing_RV_E64
            - apps/gaussian_RV
            - tests/bit8_packing_test_RV
            - tests/bit8_unpack_test_RV
            - tests/fp_get_shared_exp_test_RV''',

        '''behavioral_mu_tests:  # 42m build 12226
            - apps/pointwise_mu_io_RV_E64
            - apps/pointwise_mu_io_RV_E64_MB
            - apps/abs_max_full_unroll_fp_RV
            - apps/get_e8m0_scale_test_fp_RV_E64_MB
            - apps/get_apply_e8m0_scale_fp_RV''',

        '''hardcoded_dense_tests:  # 8m build 12226
            - apps/unsharp_RV''',
    )
    # ------------------------------------------------------------------------
    # pr_aha5
    # ------------------------------------------------------------------------
    configs['pr_aha5'] = combine(
        {},
        '''no_zircon_sparse_tests:  # 19m build 12226
              - vec_elemmul
              - mat_vecmul_ij
              - mat_elemadd_leakyrelu_exp
              - matmul_ikj
              - tensor3_mttkrp''',

        '''glb_tests:  # 85m build 12226
            - apps/pointwise
            - apps/maxpooling
            - tests/bit8_packing_test
            - tests/bit8_unpack_test
            - tests/fp_get_shared_exp_test
            - tests/fp_e8m0_quant_test
            - apps/camera_pipeline_2x2
            - apps/gaussian
            - apps/harris_color
            - apps/unsharp''',

        '''glb_tests_fp:  # 29m build 12226
            - tests/fp_arith
            - tests/fp_comp
            - apps/matrix_multiplication_fp
            - apps/relu_layer_fp
            - apps/scalar_max_fp
            - apps/scalar_avg_fp'''
    )
    # ------------------------------------------------------------------------
    # pr_aha6
    # ------------------------------------------------------------------------
    configs['pr_aha6'] = combine({},
        '''resnet_tests:  # 126m build 12226
            - conv1
            - conv2_x
            - conv5_x
    ''')
    #, '''resnet_tests_fp:  # 0m build 12226 - not yet supported by zircon
    #             - conv2_x_fp'''

    # ------------------------------------------------------------------------
    # pr_aha7
    # ------------------------------------------------------------------------
    configs['pr_aha7'] = combine(
        resnet18_conv2d6,     # 46m
        resnet18_conv2d11,    # 28m
        resnet18_conv2dfake,  # 22m
        resnet18_conv2d16,    # 44m
    )
    # ------------------------------------------------------------------------
    # pr_aha8
    # ------------------------------------------------------------------------
    configs['pr_aha8'] = yaml.safe_load(
        '''glb_tests_fp_RV:  # 28m build 12226
              - tests/fp_arith_RV
              - tests/fp_comp_RV
              - apps/relu_layer_fp_RV
              - apps/relu_layer_multiout_fp_RV
              - apps/avgpool_layer_fp_RV_E64
              - apps/mat_vec_mul_fp_RV
              - apps/scalar_reduction_fp_RV
              - apps/scalar_max_fp_RV
              - apps/layer_norm_pass2_fp_RV
              - apps/layer_norm_pass3_fp_RV
              - apps/scalar_avg_fp_RV
              - apps/stable_softmax_pass2_fp_RV
              - apps/stable_softmax_pass3_fp_RV
              - apps/vector_reduction_fp_RV
              - apps/gelu_pass1_fp_RV
              - apps/gelu_pass2_fp_RV
              - apps/silu_pass1_fp_RV
              - apps/silu_pass2_fp_RV
              - apps/swiglu_pass2_fp_RV
              - apps/rope_pass1_fp_RV
              - apps/rope_pass2_fp_RV
        ''')
    # ------------------------------------------------------------------------
    # pr_aha9
    # ------------------------------------------------------------------------
    configs['pr_aha9'] = combine(
        resnet18_zdqr,      # 82m build 12226
        resnet18_submod15,  # 28m build 12226
    )
    # ------------------------------------------------------------------------
    # pr_aha
    # ------------------------------------------------------------------------
    configs['pr_aha'] = combine(
        configs['pr_aha1'].copy(),  # First dict becomes an alias if already exists!!
        configs['pr_aha2'],
        configs['pr_aha3'],
        configs['pr_aha4'],
        configs['pr_aha5'],
        configs['pr_aha6'],
        configs['pr_aha7'],
        configs['pr_aha8'],
        configs['pr_aha9'],
    )

    # ------------------------------------------------------------------------
    # List of tests that can run with E64 mode
    # ------------------------------------------------------------------------
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
        "apps/zircon_psum_reduction_fp",
        "apps/zircon_dequantize_relu_fp"
    ]

    # List of tests that can run with E64 multi_bank mode,
    E64_MB_supported_tests = [
        "apps/pointwise",
        "apps/pointwise_mu_io",
        "apps/pointwise_custom_place_multibank",
        "apps/get_e8m0_scale_test_fp",
        "apps/zircon_residual_relu_fp",
        "apps/zircon_nop",
        "apps/zircon_psum_reduction_fp",
        "apps/zircon_dequantize_relu_fp"
    ]

    # -----------------------------------------------------------------------------------
    # skip_cgra_map: These tests skip CGRA mapping and pnr to save time.  We assume that
    # the collateral was generated by a prior test. This means certain tests must be run
    # in order e.g. map/pnr for resnet18-mod17-kernel0 can also be used for kernels 1,2,3,...
    # ------------------------------------------------------------------------------------
    # FIXME/TODO can replace this mechanism with a simple "if test ~ /kernel/ and test ~~ /kernel0... in regress.py...right?
    # ------------------------------------------------------------------------------------
    skip_cgra_map = [
        "resnet18-conv2d_mx_default_16 -> zircon_nop_post_conv5_x_kernel1_RV_E64_MB",
        "resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel1_RV_E64_MB",
        "resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel2_RV_E64_MB",
        "resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel3_RV_E64_MB",
        "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB",
        "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel2_RV_E64_MB",
        "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel3_RV_E64_MB",
    ]

    # ------------------------------------------------------------------------------------
    # Methods begin here
    # ------------------------------------------------------------------------------------
    def __init__(self, testname="BLANK", zircon=True):

        self.__dict__.update(Tests.template.copy())
        if testname in Tests.configs:
            self.__dict__.update(Tests.configs[testname])

        elif self.detect_and_process_json(testname):
            return

        elif self.detect_and_process_yaml(testname):
            return

        else:
            ########################################################################
            # FIXME This option exists solely to support the existing 'app' utility.
            # Can delete when/if 'app' gets updated to use something better
            # (e.g. command-line or file-indirect json / yaml)
            self.process_file(testname)
            return

    def process_file(self, config):
        '''
        # Read a custom config from external file <config>.py
        # E.g. if we find a config file '/aha/aha/util/regress_tests/custom4485.py' containing
        #   "if True:
        #       width, height = 4, 2
        #       glb_tests = [ 'tests/pointwise' ]"
        # then 'aha regress custom4485' would run a 4x2 pointwise test.
        '''
        import os, sys

        # Canonicalize filename (must have .py extension)
        # and module name (must *not* have .py extension)
        filename = config if config[-3:] == '.py' else config+'.py'
        module = filename[:-3]  # Module name is filename with .py extension stripped off

        # Find the file
        print(f"Is {config} a python file in our search path?")
        for p in sys.path:
            fullpath = p + '/' + filename
            if os.path.exists(fullpath): break
            else: fullpath = False

        if not fullpath:
            print(f"\nCould NOT find {filename} in {sys.path=}", flush=True)
            exit(13)

        # print(f"- Yes! Found {fullpath}\n")
        print(f"- Yes! Found module '{module}' in dir '{p}'\n")

        # Use python3 to see if file has correct syntax
        from subprocess import run, PIPE
        print("Is it a *parsable* python file? ", flush=True)
        p = run(f'python3 {filename}', shell=True, stderr=sys.stderr)
        sys.stdout.flush()
        if p.returncode: exit(p.returncode)
        else: print("Yes!\n")

        import importlib
        print("Load the module and use its local vars as config")
        md = importlib.import_module(module).__dict__
        config_dict = Tests.template.copy()
        for key in config_dict:
            if key in md: config_dict[key] = md[key]

        # Update self parms and return
        self.__dict__.update(config_dict)
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
    
    def show_config(config_name='', zircon=True):
        # Dump regression suite contents in compact form e.g. show_config('fast'):
        #
        # fast    sparse_tests   vec_identity             8x8 --removed 4 --mu 8
        # fast    glb_tests      apps/pointwise           8x8 --removed 4 --mu 8
        # fast    glb_tests      apps/pointwise_RV_E64    8x8 --removed 4 --mu 8
        # fast    glb_tests      apps/pointwise_RV_E64_MB 8x8 --removed 4 --mu 8
        # fast    glb_tests_fp   tests/fp_pointwise       8x8 --removed 4 --mu 8

        # Find config and populate it with default keys from template
        d = Tests.template.copy()
        d.update(Tests.configs[config_name])

        (w,h) =  (d['width'], d['height'])
        (col,mu) = (d["cols_removed"], d["mu_oc_0"])

        # Setup up the format string for parms e.g. "8x8 --removed 4 --mu 8"
        size = "%sx%s" % (w,h)                       # "8x8"
        zparms = " --removed %s --mu %s" % (col,mu)  # "--removed 4 --mu 8"
        if zircon: parms = size + zparms
        else:      parms = size + ' --no-zircon'

        not_groups = ("width", "height", "cols_removed", "mu_oc_0")
        for group in d:
            if not d[group]:               continue  # Dont care about empty sets
            if group in not_groups:        continue  # Not a group
            if "supported_tests" in group: continue  # Also not a group
            for app in d[group]:
                fmt = "%-12s %-16s %-32s %-s"
                print(fmt % (config_name, group, app, parms))
                # rval += (fmt % (config_name, group, app, d["app_parms"]))

    # PR_SUBMOD tests for push/pull from aha submod repos
    # FIXME ask yuchen and michael if they use this? then DELETE IT maybe
    configs['pr_submod'] = {
        "width": 28,
        "height": 16,
        "mu_oc_0": 32,
        "cols_removed": 12,

        "behavioral_mu_tests": [
            "apps/pointwise_mu_io_RV_E64",
            "apps/pointwise_mu_io_RV_E64_MB",
            "apps/abs_max_full_unroll_fp_RV",
            "apps/get_e8m0_scale_test_fp_RV_E64_MB",
            "apps/get_apply_e8m0_scale_fp_RV"
        ],
        "external_mu_tests": [
            "resnet18-conv2d_mx_default_6 -> zircon_nop_post_conv3_x_RV_E64_MB",
            "resnet18-conv2d_mx_default_11 -> zircon_nop_post_conv4_x_RV_E64_MB",
            "fakeconv2d-conv2d_mx_default -> zircon_nop_post_fakeconv2d_RV_E64_MB",
            "resnet18-conv2d_mx_default_16 -> zircon_nop_post_conv5_x_kernel0_RV_E64_MB",
            "resnet18-conv2d_mx_default_16 -> zircon_nop_post_conv5_x_kernel1_RV_E64_MB"
        ],
        "external_mu_tests_fp": [
            "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB",
            "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB",
            "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel2_RV_E64_MB",
            "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel3_RV_E64_MB",
            "resnet18-submodule_3 -> zircon_residual_relu_fp_post_conv2_x_RV_E64_MB",
            "resnet18-submodule_7 -> zircon_residual_relu_fp_post_conv3_x_RV_E64_MB",
            "resnet18-submodule_11 -> zircon_residual_relu_fp_post_conv4_x_inner_reduction_workaround_RV_E64_MB",
            "resnet18-submodule_15 -> zircon_residual_relu_fp_post_conv5_x_inner_reduction_workaround_RV_E64_MB",
            "resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel0_RV_E64_MB",
            "resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel1_RV_E64_MB",
            "resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel2_RV_E64_MB",
            "resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel3_RV_E64_MB"
        ],
        "glb_tests": [
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
            "tests/fp_e8m0_quant_test"
        ],
        "glb_tests_RV": [
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
            "apps/gaussian_RV"
        ],
        "glb_tests_fp": [
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
            "apps/rope_pass2_fp"
        ],
        "glb_tests_fp_RV": [
            "tests/fp_pointwise_RV",
            "tests/fp_arith_RV",
            "tests/fp_comp_RV",
            "apps/relu_layer_fp_RV",
            "apps/relu_layer_multiout_fp_RV",
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
            "apps/mat_vec_mul_fp_RV"
        ],
        "hardcoded_dense_tests": [
            "apps/unsharp_RV"
        ],
        "no_zircon_sparse_tests": [
            "vec_elemmul",
            "mat_vecmul_ij",
            "mat_elemadd_leakyrelu_exp",
            "matmul_ikj",
            "tensor3_mttkrp"
        ],
        "resnet_tests": [],
        "resnet_tests_fp": [],
        "sparse_tests": [
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
            "mat_vecmul_iter",
            "tensor3_elemadd",
            "tensor3_ttm",
            "tensor3_ttv"
        ],
    }
    # submod

    # FULL test is used by scheduled weekly aha regressions
    configs['full'] = {
        "width": 28,
        "height": 16,
        "mu_oc_0": 32,
        "cols_removed": 12,
    # full
        "behavioral_mu_tests": [
            "apps/pointwise_mu_io_RV_E64",
            "apps/pointwise_mu_io_RV_E64_MB",
            "apps/abs_max_full_unroll_fp_RV",
            "apps/get_e8m0_scale_test_fp_RV_E64_MB",
            "apps/get_apply_e8m0_scale_fp_RV"
        ],
    # full
        "external_mu_tests": [
            "resnet18-conv2d_mx_default_6 -> zircon_nop_post_conv3_x_RV_E64_MB",
            "resnet18-conv2d_mx_default_11 -> zircon_nop_post_conv4_x_RV_E64_MB",
            "fakeconv2d-conv2d_mx_default -> zircon_nop_post_fakeconv2d_RV_E64_MB",
            "resnet18-conv2d_mx_default_16 -> zircon_nop_post_conv5_x_kernel0_RV_E64_MB",
            "resnet18-conv2d_mx_default_16 -> zircon_nop_post_conv5_x_kernel1_RV_E64_MB"
        ],
    # full
        "external_mu_tests_fp": [
            "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB",
            "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB",
            "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel2_RV_E64_MB",
            "resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel3_RV_E64_MB",
            "resnet18-submodule_3 -> zircon_residual_relu_fp_post_conv2_x_RV_E64_MB",
            "resnet18-submodule_7 -> zircon_residual_relu_fp_post_conv3_x_RV_E64_MB",
            "resnet18-submodule_11 -> zircon_residual_relu_fp_post_conv4_x_inner_reduction_workaround_RV_E64_MB",
            "resnet18-submodule_15 -> zircon_residual_relu_fp_post_conv5_x_inner_reduction_workaround_RV_E64_MB",
            "resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel0_RV_E64_MB",
            "resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel1_RV_E64_MB",
            "resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel2_RV_E64_MB",
            "resnet18-submodule_17 -> zircon_residual_relu_fp_post_conv5_x_kernel3_RV_E64_MB"
        ],
    # full
        "glb_tests": [
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
            "apps/matrix_multiplication"
        ],
    # full
        "glb_tests_RV": [
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
            "apps/pointwise_custom_packing_RV_E64"
        ],
    # full
        "glb_tests_fp": [
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
            "apps/rope_pass2_fp"
        ],
    # full
        "glb_tests_fp_RV": [
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
            "apps/avgpool_layer_fp_RV_E64",
            "apps/mat_vec_mul_fp_RV"
        ],
    # full
        "hardcoded_dense_tests": [
            "apps/unsharp_RV"
        ],
    # full
        "no_zircon_sparse_tests": [
            "vec_elemmul",
            "mat_vecmul_ij",
            "mat_elemadd_leakyrelu_exp",
            "matmul_ikj",
            "tensor3_mttkrp"
        ],
    # full
        "resnet_tests": [
            "conv1",
            "conv2_x",
            "conv5_x"
        ],
    # full
        "resnet_tests_fp": [
            "sequential_0_fp",
            "InvRes1_pw_fp",
            "InvRes2_pw_exp_fp",
            "InvRes2_pw_sq_fp",
            "InvRes3_pw_exp_fp",
            "InvRes3_pw_sq_residual_fp"
        ],
    # full
        "sparse_tests": [
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
            "fp_matmul_ikj"
        ],
    }

# Every time someone tries to import this class, it triggers this
# quick check to make sure that no configs have redundant apps

errors = ''
for config_name in Tests.configs:
    DBG=0
    if DBG: print('\n', config_name)
    config = Tests.configs[config_name]
    lists = [key for key in config if type(config[key]) is list]
    for group in lists:
        apps = config[group]
        if DBG: print(f'    Config {config_name} has list {key}')
        for app in set(apps):  # Use set to prevent duplicate checks
            n_app = apps.count(app)
            if n_app > 1:
                errors += f"    ERROR: Config {config_name}[{group}] has {n_app} copies of '{app}'\n"

assert not errors, 'Found duplicate apps, see ERROR messages above\n\n' + errors
