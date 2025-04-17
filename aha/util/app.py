#   EXAMPLE(S):
#     aha app 4x2 apps/pointwise
#     aha app 4x2 tests/fp_pointwise
#     aha app 4x2 tests/fp_pointwise --waveform
#     aha app 4x2 tests/fp_pointwise --cols-removed 4 --mu 8
#     aha app --verilator 4x2 apps/pointwise --cols-removed 4 --mu 8

# For help/details do 'aha app --help'

from pathlib import Path
import subprocess
def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.set_defaults(dispatch=dispatch)

def dispatch(args, extra_args=None):
    print(["/aha/aha/bin/app"] + extra_args)
    subprocess.call(["/aha/aha/bin/app"] + extra_args)
