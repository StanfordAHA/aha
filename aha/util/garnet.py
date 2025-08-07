from pathlib import Path
import subprocess
import os
import sys


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.set_defaults(dispatch=dispatch)


# FIXME/TODO this function is same in pnr.py, granet.py, regress.py...
def retry(r_func, *args, **kwargs):
    for retry in [1, 2, 3]:  # In case of SIG error, retry up to three times
        print(f"--- TRY attempt #{retry} {args=}", flush=True)
        try:
            r_func(*args, **kwargs); break

        except subprocess.CalledProcessError as e:
            retry_sigs = [ 'SIGSEGV','SIGBUS','SIGABRT']; found_retry_sig = False
            for rs in retry_sigs:
                if rs in str(e): found_retry_sig = True

            if found_retry_sig:
                print(f'\n\n{e}\n')  # Print the error msg
                print(f'*** ERROR subprocess died {retry} time(s) with one of {retry_sigs}')
                print('*** Will retry twice more, then give up.\n\n', flush=True)

                # if retry == 3: raise
                # - No! Don't raise the error! Higher-level aha.py has similar
                # - three-retry catchall, resulting in up to nine retries ! (Right?)
                # - Do this instead:
                if retry == 3:
                    assert False, 'ERROR: Three time loser'
            else:
                raise

def dispatch(args, extra_args=None):
    retry(
        subprocess.check_call,
        [sys.executable, "garnet.py"] + extra_args, cwd=args.aha_dir / "garnet"
    )
