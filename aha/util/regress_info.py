# Turns timing-table input into a readable summary table, e.g.
# 
#     example_input=[
#         ["garnet (Zircon) with sparse and dense",                     1588 ],
#         ["APP GROUP sparse_tests[]",                                     0 ],
#         ["gen_sparse_bitstreams",                                     3018 ],
#         ["vec_elemmul_glb",                                            143 ],
#         ["APP GROUP glb_tests_RV[]",                                     0 ],
#         ["APP GROUP glb_tests_fp_RV[]",                                  0 ],
#         ["resnet18-quantize_default_1::zircon_quant_fp_post_conv2",   2630 ],
#         ["resnet18-quantize_default_3::zircon_quant_fp_post_conv2x",  1363 ],
#         ["resnet18-quantize_default_15::zircon_quant_fp_post_conv5x", 1260 ],
#         ["APP GROUP external_mu_tests[]",                                0 ],
#     ]
#     example_output = '''
#         0h26 garnet (Zircon) with sparse and dense
# 
#         1h01 APP GROUP sparse_tests[]
#              0h50 gen_sparse_bitstreams
#              0h02 vec_elemmul_glb
# 
#         1h27 APP GROUP voyager_cgra_tests_fp[]
#              0h43 resnet18-quantize_default_1::zircon_quant_fp_post_conv2x
#              0h22 resnet18-quantize_default_3::zircon_quant_fp_post_conv2x
#              0h21 resnet18-quantize_default_15::zircon_quant_fp_post_conv5x
#     '''

def summarize_and_print_info(info):
    'Print a readable summary of the info table. Try not to swizzle it!'
    if not info: return
    info1 = appgroups(info.copy())  # NO SWIZZO!
    info2 = eliminate_skips(info1)
    # length_of_longest_line = max( [len(e) for e in info2] )
    # hline = length_of_longest_line * '-'
    hline = 120 * '_'
    print(hline)
    print(" Time(hhmm)   App")
    print("------------ --------------------------------------------------------------------------------")
    for line in info2: print(line)
    print(hline)

def eliminate_skips(info1):
    '''
    Delete SKIP lines and add their info to the first non-skip line after e.g.

    BEFORE:
          49 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB_MU_ext
           0 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB/zircon_dequantize_relu_fp_post_conv1_kernel1 - SKIP CGRA MAP
           0 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB/zircon_dequantize_relu_fp_post_conv1_kernel1 - SKIP CGRA PNR
          21 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB_MU_ext

    AFTER:
          49 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB_MU_ext
          21 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB_MU_ext [SKIP MAP,PNR]
    '''
    info2,skip = ([],[])
    for line in info1:
        if "SKIP" in line:
            if   "MAP" in line: skip += ['MAP']
            elif "PNR" in line: skip += ['PNR']
            elif "OUTPUT PIPELINE REG" in line: skip += ['OREG']
            continue
        else:
            # E.g. "[SKIP MAP,PNR]"
            skip = ' [SKIP ' + (',').join(skip) + ']' if skip else ''
            info2.append(line+skip)
            skip = []
    return info2

def appgroups(info1):
    '''
    # - calculate grouptimes
    # - add blank lines before each "APP GROUP" and garnet "NO Zircon" compilation
    # - indent app names
    # - make separate columns for app times, group times
    # - times FIRST, then names why not

    # Each info1 input line should be in form ['appname','apptime']
    # Each info2 output line will be in the form [groupname, grouptime, ''] or [appname, '', apptime]

    BEFORE:
    ["garnet (Zircon) with sparse and dense", 1588]
    ["APP GROUP external_mu_tests_fp[]",         0]
    ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB_MU_ext", 2972 ],
    ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB/zirc... - SKIP CGRA MAP", 0]
    ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB/zirc... - SKIP CGRA PNR", 0]
    ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB_MU_ext", 1277 ],
    ...

    AFTER:
         26 garnet (Zircon) with sparse and dense

       4h20 APP GROUP external_mu_tests_fp[]
              49 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB_MU_ext
              21 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB_MU_ext [SKIP MAP,PNR]
              ...
    '''
    def hhmm(nsec):
        'Turn nsec into hhmm e.g. hhmm(3600)="1h00" or hhmm(120)="0h02" '
        (nmin,nhrs) = (nsec//60,nsec//3600)
        if False: hhmm = f'{nmin:.0f}'                      # "1"  "59"
        else:         hhmm = f'{nmin//60:.0f}h{nmin%60:02.0f}'  # "1h25"
        return f'{hhmm:>6}'


    info2 = []   # Output table goes here
    (grouptotal,ngroupapps) = (0,0)
    blankline = ['','','']

    # Easy to count group times if go through list in reverse order, yes?
    info1.reverse()
    for line1 in info1:
        # Set name and time e.g. if line1=['pointwise', 0] then name='pointwise' and time=0
        (name,time) = ('',0)
        for e in line1:  # This works even if "line" is scalar or 1-element list
            if   not name: name=e
            elif not time: time=e

        if name.startswith("APP GROUP") or name.startswith("garnet "):
            if not ngroupapps: continue  # Skip groups that ran 0 apps
            line2 = f'{hhmm(grouptotal)} {name}'
            (grouptotal,ngroupapps) = (0,0)
        else:
            line2 = f'     {hhmm(time)} {name}'  # Indent app name
            grouptotal += time
            ngroupapps += 1
        info2.append(line2)

        # add blank lines before each "APP GROUP" and garnet "NO Zircon" compilation
        if name.startswith("APP GROUP") or "NO Zircon" in name or "garnet with dense" in name:
            info2.append("")
    info2.reverse()
    print("FOOO",info2,"------------------")
    return info2

##############################################################################
# Crude testing support

DO_TEST1 = False
DO_TEST2 = False

# Test1: what if app runs in 0 seconds, does it still print the group heading.
if DO_TEST1:
  summarize_and_print_info(\
[
 ["garnet (Zircon) with sparse and dense",          998 ],
 ["APP GROUP dense_ml_models[]",                      0 ],
 ["APP GROUP dense_ml_unit_tests[]",                  0 ],
 ["pointwise_voyager_full_model",                     0 ],
 ["APP GROUP sparse_tests[]",                         0 ],
 ["APP GROUP glb_tests_RV[]",                         0 ],
 ["APP GROUP glb_tests_fp_RV[]",                      0 ],
 ["APP GROUP behavioral_mu_tests[]",                  0 ],
 ["APP GROUP voyager_cgra_tests_fp[]",                0 ],
 ["APP GROUP external_mu_tests[]",                    0 ],
 ["APP GROUP external_mu_tests_fp[]",                 0 ],
])

# Test2: what does a normal run look like
if DO_TEST2:
  summarize_and_print_info(\
[
 ["garnet (Zircon) with sparse and dense",                                         1588 ],
 ["APP GROUP sparse_tests[]",                                                         0 ],
 ["gen_sparse_bitstreams",                                                         3018 ],
 ["vec_elemmul_glb",                                                                143 ],
 ["mat_vecmul_ij_glb",                                                              135 ],
 ["mat_sddmm_glb",                                                                  135 ],
 ["tensor3_mttkrp_glb",                                                             139 ],
 ["tensor3_ttv_glb",                                                                135 ],
 ["APP GROUP glb_tests_RV[]",                                                         0 ],
 ["APP GROUP glb_tests_fp_RV[]",                                                      0 ],
 ["APP GROUP behavioral_mu_tests[]",                                                  0 ],
 ["APP GROUP voyager_cgra_tests_fp[]",                                                0 ],
 ["resnet18-quantize_default_1::zircon_quant_fp_post_conv2x_RV_E64_MB_voyager_standalone_cgra",    2630 ],
 ["resnet18-quantize_default_3::zircon_quant_fp_post_conv2x_RV_E64_MB_voyager_standalone_cgra",    1363 ],
 ["resnet18-quantize_default_15::zircon_quant_fp_post_conv5x_RV_E64_MB_voyager_standalone_cgra",   1260 ],
 ["APP GROUP external_mu_tests[]",                                    0 ],
 ["APP GROUP external_mu_tests_fp[]",                                 0 ],
 ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB_MU_ext",                                                           2972 ],
 ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB/zircon_dequantize_relu_fp_post_conv1_kernel1 - SKIP CGRA MAP",        0 ],
 ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB/zircon_dequantize_relu_fp_post_conv1_kernel1 - SKIP CGRA PNR",        0 ],
 ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB_MU_ext",                                                           1277 ],
 ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel2_RV_E64_MB/zircon_dequantize_relu_fp_post_conv1_kernel2 - SKIP CGRA MAP",        0 ],
 ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel2_RV_E64_MB/zircon_dequantize_relu_fp_post_conv1_kernel2 - SKIP CGRA PNR",        0 ],
 ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel2_RV_E64_MB_MU_ext",                                                           7128 ],
 ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel3_RV_E64_MB/zircon_dequantize_relu_fp_post_conv1_kernel3 - SKIP CGRA MAP",        0 ],
 ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel3_RV_E64_MB/zircon_dequantize_relu_fp_post_conv1_kernel3 - SKIP CGRA PNR",        0 ],
 ["resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel3_RV_E64_MB_MU_ext",                                                           4254 ],
])
