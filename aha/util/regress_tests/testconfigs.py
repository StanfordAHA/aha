#!/usr/bin/env python3
import sys
import json
import yaml
import subprocess
from tests import Tests
from contextlib import redirect_stdout
'''
TODO: how do we make this work as pytests?
'''

# Helper routine
def compare_configs(wanted, got):
    'Verbose comparison of two dictionaries, throw error if they differ'
    err = False
    for key in set(list(wanted.keys()) + list(got.keys())):
        if key not in wanted:
            print(f"*** ERROR: Returned config has extra {{ {key} : {got[key]} }}"); err = True
        elif key not in got:
            print(f"*** ERROR: Returned config should have {key}= {wanted[key]}"); err = True
        elif wanted[key] != got[key]:
            print(f'*** ERROR: Wanted "{key} : {wanted[key]}", got "{key} : {got[key]}"'); err = True
    if err:
        print(''); return False
    else:
        return True

# Helper constant for test_json, test_yaml
pointwise = {
    "width": 8, "height": 8, "mu_oc_0": 32, "cols_removed": 12,
    "glb_tests": [ "apps/pointwise" ],
    #---------------------------------
    "behavioral_mu_tests": [],
    "external_mu_tests": [],
    "external_mu_tests_fp": [],
    "glb_tests_RV": [],
    "glb_tests_fp": [],
    "glb_tests_fp_RV": [],
    "hardcoded_dense_tests": [],
    "no_zircon_sparse_tests": [],
    "resnet_tests": [],
    "resnet_tests_fp": [],
    "sparse_tests": [],
}

########################################################################
# Tests begin here

def test_imported_tests(DBG=1):
    'Mimic regress.py imported_tests mechanism to ensure that it works'
    print("Testing imported_tests mechanism\n")

    imported_tests = None

    config = 'fast'
    imported_tests = Tests(config)
    #     print(imported_tests)

    parms = Tests.parmnames    # [ 'width', 'height',' num_fabric_cols_removed', 'mu_oc_0']
    print(parms); exit()


    OLD_STYLE = True
    if OLD_STYLE:
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
        behavioral_mu_tests = imported_tests.behavioral_mu_tests
        external_mu_tests = imported_tests.external_mu_tests
        external_mu_tests_fp = imported_tests.external_mu_tests_fp
        hardcoded_dense_tests = imported_tests.hardcoded_dense_tests
        no_zircon_sparse_tests = imported_tests.no_zircon_sparse_tests

    else:
        parms = Tests.parmnames    # [ 'width', 'height',' num_fabric_cols_removed', 'mu_oc_0']
        groups = Tests.groupnames  # [ 'glb_tests','sparse_tests', ... ]

    print(' - width');   assert width   == imported_tests.width
    print(' - height');  assert height  == imported_tests.height
    print(' - mu_oc_0'); assert mu_oc_0 == imported_tests.mu_oc_0
    print(' - num_fabric_cols_removed'); assert num_fabric_cols_removed == imported_tests.cols_removed
    print()
    print(' - glb_tests');        assert glb_tests       == imported_tests.glb_tests
    print(' - glb_tests_fp');     assert glb_tests_fp    == imported_tests.glb_tests_fp
    print(' - glb_tests_RV');     assert glb_tests_RV    == imported_tests.glb_tests_RV
    print(' - glb_tests_fp_RV');  assert glb_tests_fp_RV == imported_tests.glb_tests_fp_RV
    print()
    print(' - sparse_tests');     assert sparse_tests    == imported_tests.sparse_tests
    print(' - resnet_tests');     assert resnet_tests    == imported_tests.resnet_tests
    print(' - resnet_tests_fp');  assert resnet_tests_fp == imported_tests.resnet_tests_fp
    print()
    print(' - external_mu_tests');      assert external_mu_tests      == imported_tests.external_mu_tests
    print(' - external_mu_tests_fp');   assert external_mu_tests_fp   == imported_tests.external_mu_tests_fp
    print(' - behavioral_mu_tests');    assert behavioral_mu_tests    == imported_tests.behavioral_mu_tests
    print(' - hardcoded_dense_tests');  assert hardcoded_dense_tests  == imported_tests.hardcoded_dense_tests
    print(' - no_zircon_sparse_tests'); assert no_zircon_sparse_tests == imported_tests.no_zircon_sparse_tests

# cat << eof | awk '{printf("    print(|%s|); %s\n", $2, $0)}' | sed "s/|/'/g"
#     assert width == imported_tests.width
#     assert height == imported_tests.height
#     assert num_fabric_cols_removed == imported_tests.cols_removed
#     assert mu_oc_0 == imported_tests.mu_oc_0
#     assert sparse_tests == imported_tests.sparse_tests
#     assert glb_tests == imported_tests.glb_tests
#     assert glb_tests_fp == imported_tests.glb_tests_fp
#     assert glb_tests_RV == imported_tests.glb_tests_RV
#     assert glb_tests_fp_RV == imported_tests.glb_tests_fp_RV
#     assert resnet_tests == imported_tests.resnet_tests
#     assert resnet_tests_fp == imported_tests.resnet_tests_fp
#     assert behavioral_mu_tests == imported_tests.behavioral_mu_tests
#     assert external_mu_tests == imported_tests.external_mu_tests
#     assert external_mu_tests_fp == imported_tests.external_mu_tests_fp
#     assert hardcoded_dense_tests == imported_tests.hardcoded_dense_tests
#     assert no_zircon_sparse_tests == imported_tests.no_zircon_sparse_tests
# eof




















    return


    # Print imported tests in gold-standard format

    # Copied from test_configs() below
    'Cycle through all configs in test.py and compare to gold'
    import os, json
    all_configs = list(Tests.configs.keys())
    for config_name in all_configs:

        # Get dict that lists config contents
        config = Tests(config_name).__dict__

        # Dump contents of dict to a test file for comparison
        test = f'tmp.tests-{config_name}.json'
        with open(test, 'w') as f:
            hline = 61 * '-'
            with redirect_stdout(f):
                print(f'{hline}\n44 {config_name}')
                print(json.dumps(config, indent=4, sort_keys=True))
                print(hline)
            f.close()

        # Print test contents to stdout before comparison
        # FIXME maybe this should be optional e.g. 'if DBG'
        with open(test, 'r') as f:
            content = f.read()
            print(content)
            f.close()

        # Using bash diff, compare to gold
        gold = f'gold/tests-{config_name}.json'
        cmd = f'diff {gold} {test}'; print(cmd)
        sys.stdout.flush()  # Must flush *before* diff or no stdout (??)
        a = subprocess.run(cmd, shell=True)

        os.remove(test)  # Clean up

        # Process comparison results
        err = f'\nConfig "{config_name}" does not match gold model'
        assert a.returncode == 0, err
        print("PASS")





























test_imported_tests(); exit()


def test_json(DBG=0):
    # Json string as config e.g. '{"glb_tests":["apps/pointwise"]}'
    print("Testing json string as config")
    jstring = '{"width":8,"height":8,"glb_tests":["apps/pointwise"]}'
    jconfig = Tests(jstring).__dict__
    if DBG: print("Want:", json.dumps(pointwise, indent=4, sort_keys=True))
    if DBG: print("Found:", json.dumps(jconfig, indent=4, sort_keys=True))
    print("Checking against known desired output...")
    assert compare_configs(pointwise, jconfig)
    print("PASS json test\n")

def test_yaml(DBG=0):
    # Yaml string as config e.g. "glb_tests:\n- apps/pointwise"
    print("Testing yaml string as config")
    ystring = "width: 8\nheight: 8\nglb_tests:\n- apps/pointwise"
    yconfig = Tests(ystring).__dict__
    DBG=0
    if DBG: print("Want:", json.dumps(pointwise, indent=4, sort_keys=True))
    if DBG: print("Found:", json.dumps(yconfig, indent=4, sort_keys=True))
    assert compare_configs(pointwise, yconfig)
    print("PASS yaml test\n")

def test_customfile(DBG=0):
    '''
    Read a custom config from external python file <testname>
    E.g. "tmp.py" where tmp.py has local vars with valid config components e.g.
      % cat tmp.py
      if True:
          width,height = 8,8
          glb_tests = [ 'tests/pointwise' ]
    '''
    import os, sys
    from subprocess import run, PIPE
    print("Testing custom python file as config")

    # Prepare the custom file
    tmpfile = 'tmp-aha-test-tests.py'
    with open(tmpfile, 'w') as f:
        print('''if True:
          width,height = 8,8
          glb_tests = [ 'apps/pointwise' ]
        ''', file=f)
        f.close()
    print(f"File {tmpfile} contains:\n    ", flush=True, end='')
    run(f'cat {tmpfile}', shell=True, stderr=sys.stderr, stdout=sys.stdout)
    sys.stdout.flush()

    # Try using custom file as config
    fdict = Tests(tmpfile).__dict__

    # Delete the custom file now that we are done
    os.remove(tmpfile)
    
    # See if config results match what we wanted
    assert compare_configs(pointwise, fdict)
    print("PASS custom-config-file test\n")

def test_supported_tests():
    err = 'E64_MB_supported_tests broken'
    assert "apps/pointwise" in Tests.E64_MB_supported_tests, err

def test_skip_cgra():
    err = 'skip_cgra_map broken'
    t="resnet18-conv2d_mx_default_16 -> zircon_nop_post_conv5_x_kernel1_RV_E64_MB"
    assert t in Tests.skip_cgra_map

def test_configs():
    'Cycle through all configs in test.py and compare to gold'
    import os, json
    all_configs = list(Tests.configs.keys())
    for config_name in all_configs:

        # Get dict that lists config contents
        config = Tests(config_name).__dict__

        # Dump contents of dict to a test file for comparison
        test = f'tmp.tests-{config_name}.json'
        with open(test, 'w') as f:
            hline = 61 * '-'
            with redirect_stdout(f):
                print(f'{hline}\n44 {config_name}')
                print(json.dumps(config, indent=4, sort_keys=True))
                print(hline)
            f.close()

        # Print test contents to stdout before comparison
        # FIXME maybe this should be optional e.g. 'if DBG'
        with open(test, 'r') as f:
            content = f.read()
            print(content)
            f.close()

        # Compare to gold and clean up
        gold = f'gold/tests-{config_name}.json'
        cmd = f'diff {gold} {test}'; print(cmd)
        sys.stdout.flush()  # Must flush *before* diff or no stdout (??)
        a = subprocess.run(cmd, shell=True)
        os.remove(test)  # Clean up

        # Process comparison results
        err = f'\nConfig "{config_name}" does not match gold model'
        assert a.returncode == 0, err
        print("PASS")

def main():
    hline = 9*'--------'
    test_json(); print(hline)
    test_yaml(); print(hline)
    test_customfile(); print(hline)
    test_supported_tests()
    test_skip_cgra()
    test_configs()

main()
