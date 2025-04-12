from pathlib import Path
import subprocess
import os
import sys


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    for retry in [1, 2, 3]:  # In case of SIGSEGV, retry up to three times
        try:
            subprocess.check_call(
                [sys.executable, "garnet.py"] + extra_args, cwd=args.aha_dir / "garnet",
            )
            break
        except subprocess.CalledProcessError as e:
            if 'SIGSEGV' in str(e):
                print(f'\n\n{e}\n')  # Print the error msg
                print(f'*** ERROR subprocess died {retry} time(s) with SIGSEGV')
                print('*** Will retry three times, then give up.\n\n')

                # if retry == 3: raise
                # - No! Don't raise the error! Higher-level aha.py has similar
                # - three-retry catchall, resulting in up to nine retries ! (Right?)
                # - Do this instead:
                if retry == 3:
                    assert False, 'ERROR: Three time loser'
            else:
                raise
