### What is tests.py?
`tests.py` is responsible for supplying lists of tests to `regress.py`, i.e. if someone does `aha regress fast`, `regress.py` does something like
```
    from aha.util.regress_tests.tests import Tests
    ...
    imported_tests = Tests("fast")
```
At this point, `imported_tests` is a handle for class variables
defining the `fast` config tests and setup, e.g.
```
  imported_tests.width, imported_tests.height = 8, 8
  imported_tests..glb_tests_RV = ["tests/conv_2_1_RV","apps/pointwise_RV_E64"]
  etc.
```

### Specifying custom configs
`tests.py` can detect and interpret yaml or json strings as configs e.g. the user can do one or more of these to run a single app:
```
  aha regress   'width: 8\nheight: 8\nglb_tests:\n- apps/pointwise'    # yaml
  aha regress '{"width":8,"height":8,"glb_tests":["apps/pointwise"]}'  # json
```

### Testing tests.py:

Instead of pytest (for now), can use testconfigs.py to verify tests.py directly.  This should work equally well from kiwi or docker or wherever. `testconfigs` basically exercises many of the features of tests.py, e.g. correctly listing the various configs "full", "pr_aha1", "fast", etc. and correctly interpreting json or yaml
command-line configs.
```
    python3 testconfigs.py |& less
```
