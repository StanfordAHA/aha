def summarize_and_print_info(info):
    if not info: return
    info1 = appgroups(info)
    info2 = eliminate_skips(info1)
    for line in info2: print(line)

test_info=[
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
]

sample_out = '''
  26 garnet (Zircon) with sparse and dense

1h01 APP GROUP sparse_tests[]
       50 gen_sparse_bitstreams
        2 vec_elemmul_glb
        2 mat_vecmul_ij_glb
        2 mat_sddmm_glb
        2 tensor3_mttkrp_glb
        2 tensor3_ttv_glb

1h27 APP GROUP voyager_cgra_tests_fp[]
       43 resnet18-quantize_default_1::zircon_quant_fp_post_conv2x_RV_E64_MB_voyager_standalone_cgra
       22 resnet18-quantize_default_3::zircon_quant_fp_post_conv2x_RV_E64_MB_voyager_standalone_cgra
       21 resnet18-quantize_default_15::zircon_quant_fp_post_conv5x_RV_E64_MB_voyager_standalone_cgra

4h20 APP GROUP external_mu_tests_fp[]
       49 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel0_RV_E64_MB_MU_ext
       21 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel1_RV_E64_MB_MU_ext [SKIP MAP,PNR]
     1h58 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel2_RV_E64_MB_MU_ext [SKIP MAP,PNR]
     1h10 resnet18-submodule -> zircon_dequantize_relu_fp_post_conv1_kernel3_RV_E64_MB_MU_ext [SKIP MAP,PNR]
'''

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
        'Turn nsec into hhmm e.g. hhmm(3600)="1h00" or hhmm(120)="   2" '
        (nmin,nhrs) = (nsec//60,nsec//3600)
        if nmin < 60: hhmm = f'{nmin:.0f}'                      # "1"  "59"
        else:         hhmm = f'{nmin//60:.0f}h{nmin%60:02.0f}'  # "1h25"
        return f'{hhmm:>4}'

    info2 = []       # Output table goes here
    grouptotal = 0
    blankline = ['','','']

    # Easy to count group times if go through list in reverse order, yes?
    info1.reverse()
    for line1 in info1:
        # print(f'foozy .{line1}.')
        (name,time) = ('',0)
        for e in line1:  # This works even if "line" is scalar or 1-element list
            if not name: name=e
            elif not time: time=e

        if name.startswith("APP GROUP") or name.startswith("garnet "):
            if not grouptotal: continue
            line2 = f'{hhmm(grouptotal)} {name}'
            grouptotal = 0
        else:
            line2 = f'     {hhmm(time)} {name}'  # Indent app name
            grouptotal += time
        info2.append(line2)

        # add blank lines before each "APP GROUP" and garnet "NO Zircon" compilation
        if name.startswith("APP GROUP") or "NO Zircon" in name or "garnet with dense" in name:
            info2.append("")
    info2.reverse()
    return info2

def test_info(info):
    from random import randint
    (t, t1, t2, t3, t4, t5) = 6*[randint(66,6666)]
    tsuffix='_tsuffix'
    def t0(): return randint(66,6666)
    info.append(["garnet (Zircon) with sparse and dense", t])

    info.append([f"APP GROUP sparse_tests[]", 0])
    info.append(["gen_sparse_bitstreams", t, 0, t, 0])  # Count this as "map" time
    for test in [ f'sparse-test-{i}' for i in [1,2,3] ]:
        (t, t1, t2, t3, t4, t5) = 6*[randint(66,6666)]
        info.append([test + "_glb", t0() + t1 + t2, t0(), t1, t2, t3, t4, t5])

    for tgroup in ['group1','group2','group3']:
        info.append([f"APP GROUP {tgroup}[]", 0])
        tests = [ f'{tgroup}-test{i}' for i in [1,2,3] ] + [f'{tgroup}-buzzfail']
        for unparsed_name in tests:
            (t, t1, t2, t3, t4, t5) = 6*[randint(66,6666)]
            if 'buzzfail' in unparsed_name:
                # info.append([unparsed_name+tsuffix+" FAIL"])
                info.append(["*** FAIL ***"])
                info.append(["*** FAIL " + unparsed_name+tsuffix])
                info.append(["*** FAIL ***"])
            else:
                info.append([unparsed_name+tsuffix, t0()+t1+t2, t0(), t1, t2, t3, t4, t5])

    info.append(["APP GROUP hardcoded_dense_tests[]", 0])
    info.append(["APP GROUP hardcoded_dense_tests2[]", 0])
    info.append(["APP GROUP hardcoded_dense_tests3[]", 0])

    info.append(["garnet (NO Zircon) with sparse and dense", t])
    info.append(["gen_sparse_bitstreams_nz", t, 0, t, 0])  # Count this as "map" time
    for test in [ f'sparse-test-nz{i}' for i in [1,2,3] ]:
        (t, t1, t2, t3, t4, t5) = 6*[randint(66,6666)]
        info.append([test + "_glb", t0() + t1 + t2, t0(), t1, t2, t3, t4, t5])

    for tgroup in ['group4','group5']:
        info.append([f"APP GROUP {tgroup}[]", 0])
        tests = [ f'{tgroup}-test{i}' for i in [randint(1,9)]]
        for test in tests:
            (t, t1, t2, t3, t4, t5) = 6*[randint(66,6666)]
            info.append([test + "_glb", t0() + t1 + t2, t0(), t1, t2, t3, t4, t5])

    info.append(["garnet with dense only", t])
    tests = [ f'{tgroup}-test{i}' for i in [1,2]]
    for test in tests:
        (t, t1, t2, t3, t4, t5) = 6*[randint(66,6666)]
        info.append([test + "_glb dense only", t0() + t1 + t2, t0(), t1, t2, t3, t4, t5])

# summarize_and_print_info(test_info)
